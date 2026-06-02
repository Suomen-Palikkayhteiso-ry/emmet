"""Sync command - synchronize users from Excel to Keycloak."""

from emmet.constants import INITIAL_GROUPS
from emmet.constants import REQUIRED_USER_ACTIONS
from emmet.types import User
from emmet.utils import parse_excel_users
from emmet.utils.membership import is_membership_active
from emmet.utils.membership import membership_valid_until
from emmet.utils.membership import should_skip_special_email
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError
from typing import Any
import click
import datetime
import logging
import secrets


logger = logging.getLogger(__name__)


def get_attribute_value(attributes: dict[str, Any], key: str) -> str | None:
    """Return the first Keycloak attribute value as a string."""
    value = attributes.get(key)
    if isinstance(value, list):
        if not value:
            return None
        first = value[0]
        return str(first) if first is not None else None
    return str(value) if value is not None else None


def update_existing_user(
    keycloak_admin: KeycloakAdmin,
    existing_user: dict[str, Any],
    user: User,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Update an existing Keycloak user with data from Excel.

    Args:
        keycloak_admin: The Keycloak admin client
        existing_user: The existing user dict from Keycloak
        user: The user data from Excel
        dry_run: If True, only log actions without executing them
        verbose: If True, print verbose output
    """
    existing_user_id = existing_user.get("id")
    existing_username = existing_user.get("username")

    # Get existing attributes
    existing_attributes = existing_user.get("attributes", {})
    existing_fullname = get_attribute_value(existing_attributes, "fullName")
    existing_hometown = get_attribute_value(existing_attributes, "hometown")
    existing_registration_date = get_attribute_value(
        existing_attributes, "registrationDate"
    ) or get_attribute_value(existing_attributes, "effectiveDate")
    existing_payment_date = get_attribute_value(
        existing_attributes, "paymentDate"
    ) or get_attribute_value(existing_attributes, "expirationDate")
    existing_discord = get_attribute_value(existing_attributes, "discord")
    existing_bricklink = get_attribute_value(existing_attributes, "bricklink")
    existing_brickowl = get_attribute_value(existing_attributes, "brickowl")
    legacy_date_keys_present = any(
        key in existing_attributes
        for key in [
            "effectiveDate",
            "expirationDate",
            "joinedDate",
            "membershipPaymentDate",
        ]
    )

    # Get existing first and last names
    existing_first_name = existing_user.get("firstName")
    existing_last_name = existing_user.get("lastName")

    # Determine final values: use existing if present, otherwise use new from Excel
    final_first_name = existing_first_name if existing_first_name else user.firstName
    final_last_name = existing_last_name if existing_last_name else user.lastName

    # Check for changes
    changes = []
    if existing_user.get("email") != user.email:
        changes.append(f"email: {existing_user.get('email')} → {user.email}")
    if existing_fullname != user.fullName:
        changes.append(f"fullName attribute: {existing_fullname} → {user.fullName}")
    if existing_hometown != user.hometown:
        changes.append(f"hometown attribute: {existing_hometown} → {user.hometown}")
    if existing_registration_date != user.registrationDate:
        changes.append(
            "registrationDate attribute: "
            f"{existing_registration_date} → {user.registrationDate}"
        )
    if existing_payment_date != user.paymentDate:
        changes.append(
            f"paymentDate attribute: {existing_payment_date} → {user.paymentDate}"
        )
    if existing_discord != user.discord:
        changes.append(f"discord attribute: {existing_discord} → {user.discord}")
    if existing_bricklink != user.bricklink:
        changes.append(f"bricklink attribute: {existing_bricklink} → {user.bricklink}")
    if existing_brickowl != user.brickowl:
        changes.append(f"brickowl attribute: {existing_brickowl} → {user.brickowl}")
    if legacy_date_keys_present:
        changes.append(
            "migrating legacy date attributes to registrationDate/paymentDate"
        )
    if not existing_first_name and user.firstName:
        changes.append(f"firstName: (empty) → {user.firstName}")
    if not existing_last_name and user.lastName:
        changes.append(f"lastName: (empty) → {user.lastName}")

    # Check if email is verified
    is_email_verified = existing_user.get("emailVerified", False)
    if not is_email_verified:
        changes.append("emailVerified: False → True")

    if changes:
        message = f"Updating existing user {existing_username} ({user.email})..."
        if dry_run:
            click.echo(message)
            for change in changes:
                click.echo(f"  - {change}")
        else:
            if verbose:
                logger.info(message)
            if existing_user_id:
                # Prepare attributes update
                attributes = existing_attributes.copy()
                # Remove legacy aliases when moving to canonical names.
                attributes.pop("effectiveDate", None)
                attributes.pop("expirationDate", None)
                attributes.pop("joinedDate", None)
                attributes.pop("membershipPaymentDate", None)
                if user.fullName:
                    attributes["fullName"] = [user.fullName]
                if user.hometown:
                    attributes["hometown"] = [user.hometown]
                if user.registrationDate:
                    attributes["registrationDate"] = [user.registrationDate]
                if user.paymentDate:
                    attributes["paymentDate"] = [user.paymentDate]
                if user.discord:
                    attributes["discord"] = [user.discord]
                if user.bricklink:
                    attributes["bricklink"] = [user.bricklink]
                if user.brickowl:
                    attributes["brickowl"] = [user.brickowl]

                # Use existing firstName/lastName if present, otherwise use new from Excel
                update_payload = {
                    "email": user.email,
                    "firstName": final_first_name,
                    "lastName": final_last_name,
                    "attributes": attributes,
                }
                if not is_email_verified:
                    update_payload["emailVerified"] = True
                keycloak_admin.update_user(existing_user_id, update_payload)
    else:
        if verbose:
            message = f"User {existing_username} ({user.email}) is already up-to-date"
            if dry_run:
                click.echo(message)
            else:
                logger.info(message)


def create_new_user(
    keycloak_admin: KeycloakAdmin,
    user: User,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Create a new Keycloak user with data from Excel.

    Sets a safe random password that is not meant to be remembered.
    This enables Keycloak to show the password dialog and allow sending
    a password reset email.

    Args:
        keycloak_admin: The Keycloak admin client
        user: The user data from Excel
        dry_run: If True, only log actions without executing them
        verbose: If True, print verbose output
    """
    message = f"Creating new user {user.username} ({user.email})..."

    if dry_run:
        click.echo(message)
        click.echo(
            f"  New user details: username={user.username}, email={user.email}, "
            f"firstName={user.firstName}, lastName={user.lastName}"
        )
        if INITIAL_GROUPS:
            click.echo(f"  Will be added to groups: {', '.join(INITIAL_GROUPS)}")
    else:
        if verbose:
            logger.info(message)
        # Generate a secure random password (not meant to be remembered)
        # This allows Keycloak to show password dialog and send reset emails
        random_password = secrets.token_urlsafe(32)

        # Prepare attributes
        attributes = {"locale": ["fi"]}
        if user.fullName:
            attributes["fullName"] = [user.fullName]
        if user.hometown:
            attributes["hometown"] = [user.hometown]
        if user.registrationDate:
            attributes["registrationDate"] = [user.registrationDate]
        if user.paymentDate:
            attributes["paymentDate"] = [user.paymentDate]
        if user.discord:
            attributes["discord"] = [user.discord]
        if user.bricklink:
            attributes["bricklink"] = [user.bricklink]
        if user.brickowl:
            attributes["brickowl"] = [user.brickowl]

        new_user_id = keycloak_admin.create_user(
            {
                "username": user.username,
                "email": user.email,
                "emailVerified": True,
                "firstName": user.firstName,
                "lastName": user.lastName,
                "enabled": True,
                "requiredActions": list(REQUIRED_USER_ACTIONS),
                "attributes": attributes,
                "credentials": [
                    {
                        "type": "password",
                        "value": random_password,
                        "temporary": True,
                    }
                ],
            }
        )

        # Add user to initial groups
        if new_user_id and INITIAL_GROUPS:
            for group_name in INITIAL_GROUPS:
                try:
                    # Get group by name
                    groups = keycloak_admin.get_groups({"search": group_name})
                    matching_group = next(
                        (g for g in groups if g.get("name") == group_name), None
                    )
                    if matching_group:
                        group_id = matching_group.get("id")
                        keycloak_admin.group_user_add(new_user_id, group_id)
                        if verbose:
                            logger.info(f"Added user to group: {group_name}")
                    else:
                        logger.warning(f"Group not found: {group_name}")
                except KeycloakError as e:
                    logger.error(f"Error adding user to group {group_name}: {e}")


def disable_user(
    keycloak_admin: KeycloakAdmin,
    kc_user: dict[str, Any],
    dry_run: bool,
    verbose: bool,
) -> None:
    """Disable a Keycloak user.

    Args:
        keycloak_admin: The Keycloak admin client
        kc_user: The Keycloak user dict
        dry_run: If True, only log actions without executing them
        verbose: If True, print verbose output
    """
    kc_username = kc_user.get("username")
    kc_email = kc_user.get("email")

    message = f"Disabling user {kc_username} ({kc_email})..."

    if dry_run:
        click.echo(message)
        click.echo(f"  - enabled: {kc_user.get('enabled', True)} → False")
    else:
        if verbose:
            logger.info(message)
        try:
            user_id = kc_user.get("id")
            if user_id:
                keycloak_admin.update_user(user_id, {"enabled": False})
        except KeycloakError as e:
            logger.error(f"Error disabling user {kc_username}: {e}")


@click.command()
@click.argument("excel_file", type=click.Path(exists=True))
@click.option(
    "--keycloak-server",
    envvar="KEYCLOAK_SERVER",
    required=True,
    help="Keycloak server URL.",
)
@click.option(
    "--keycloak-realm",
    envvar="KEYCLOAK_REALM",
    required=True,
    help="Keycloak realm name.",
)
@click.option(
    "--keycloak-client-id",
    envvar="KEYCLOAK_CLIENT_ID",
    required=True,
    help="Keycloak client ID.",
)
@click.option(
    "--keycloak-client-secret",
    envvar="KEYCLOAK_CLIENT_SECRET",
    required=True,
    help="Keycloak client secret.",
)
@click.option(
    "--dry-run", is_flag=True, help="Only print actions, do not execute them."
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Print verbose output.",
)
@click.option(
    "--email",
    default=None,
    help="Only sync user with this email address.",
)
def sync(
    excel_file: str,
    keycloak_server: str,
    keycloak_realm: str,
    keycloak_client_id: str,
    keycloak_client_secret: str,
    dry_run: bool,
    verbose: bool,
    email: str | None,
) -> None:
    """Synchronize users from an Excel file to Keycloak using auto-detection."""
    click.echo(f"Synchronizing users from {excel_file}...")

    if email:
        click.echo(f"Filtering to only sync user with email: {email}")
        if should_skip_special_email(email):
            logger.info(f"Skipping special-case email: {email}")
            return

    # Read users from Excel file using auto-detection
    excel_users: list[User] = parse_excel_users(excel_file, None)
    if not excel_users:
        logger.error(
            "No users found in the Excel file or an error occurred during parsing."
        )
        return

    # Filter by email if specified
    if email:
        excel_users = [user for user in excel_users if user.email == email]
        if not excel_users:
            logger.error(f"No user found with email: {email}")
            return
        logger.info(f"Found user in Excel: {excel_users[0].username} ({email})")

    # Keep only active members for provisioning:
    # last membership payment year grants access through end of following year.
    today = datetime.date.today()
    active_excel_users: list[User] = []
    inactive_excel_users: list[User] = []
    for user in excel_users:
        if should_skip_special_email(user.email):
            logger.info(f"Skipping special-case email: {user.email}")
            continue

        valid_until = membership_valid_until(user.paymentDate)
        if valid_until is None:
            inactive_excel_users.append(user)
            logger.warning(
                f"Skipping user {user.email}: missing or invalid payment date "
                f"'{user.paymentDate}'"
            )
            continue

        if is_membership_active(user, today):
            active_excel_users.append(user)
            continue

        inactive_excel_users.append(user)
        if verbose or dry_run:
            click.echo(
                f"Skipping inactive member {user.email}: membership valid until {valid_until.isoformat()}"
            )

    if email and not active_excel_users:
        logger.error(
            f"User {email} is not active: payment date is missing, invalid, or expired."
        )
        return

    if verbose:
        logger.info(
            f"Provisioning {len(active_excel_users)} active users and skipping "
            f"{len(inactive_excel_users)} inactive users."
        )

    # Connect to Keycloak
    try:
        keycloak_admin = KeycloakAdmin(
            server_url=keycloak_server,
            client_id=keycloak_client_id,
            client_secret_key=keycloak_client_secret,
            realm_name=keycloak_realm,
        )
        keycloak_admin.connection.get_token()
    except KeycloakError as e:
        logger.error(f"Error connecting to Keycloak: {e}")
        return

    # Get all users from Keycloak
    try:
        keycloak_users = keycloak_admin.get_users({})
        # Create a mapping of email -> user for existing Keycloak users
        keycloak_users_by_email = {
            user.get("email"): user for user in keycloak_users if user.get("email")
        }

        # Filter Keycloak users if email is specified
        if email:
            keycloak_users = [
                user for user in keycloak_users if user.get("email") == email
            ]
    except KeycloakError as e:
        logger.error(f"Error getting users from Keycloak: {e}")
        return

    # Sync users from Excel to Keycloak
    for user in active_excel_users:
        username = user.username
        if not username:
            logger.warning(f"Skipping user with missing username: {user}")
            continue

        if not user.email:
            logger.warning(f"Skipping user with missing email: {user}")
            continue

        try:
            # Check if user exists by email
            existing_user = keycloak_users_by_email.get(user.email)

            if existing_user:
                update_existing_user(
                    keycloak_admin, existing_user, user, dry_run, verbose
                )
            else:
                create_new_user(keycloak_admin, user, dry_run, verbose)
        except KeycloakError as e:
            logger.error(f"Error syncing user {username} ({user.email}): {e}")

    # Disable users in Keycloak that are not in the Excel file
    # Skip this step if we're filtering by email (only syncing one specific user)
    if not email:
        excel_emails = [user.email for user in active_excel_users if user.email]
        for kc_user in keycloak_users:
            kc_username = kc_user.get("username")
            kc_email = kc_user.get("email")

            # Skip if user is in Excel file
            if kc_email and kc_email in excel_emails:
                continue

            # Skip protected/special-case emails
            if should_skip_special_email(kc_email):
                logger.info(f"Skipping protected user {kc_username} ({kc_email})")
                continue

            # Skip if username is "admin" (hardcoded protection)
            if kc_username == "admin":
                logger.info(f"Skipping admin user {kc_username}")
                continue

            # Disable the user
            if kc_email:
                disable_user(keycloak_admin, kc_user, dry_run, verbose)
