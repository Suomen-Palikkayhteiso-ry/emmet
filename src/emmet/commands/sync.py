"""Sync command - synchronize users from Excel to Keycloak."""

from emmet.constants import INITIAL_GROUPS
from emmet.constants import PROTECTED_USERS
from emmet.constants import REQUIRED_USER_ACTIONS
from emmet.types import User
from emmet.utils import parse_excel_users
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError
from typing import Any
import click
import logging
import secrets


logger = logging.getLogger(__name__)


def update_existing_user(
    keycloak_admin: KeycloakAdmin,
    existing_user: dict[str, Any],
    user: User,
    dry_run: bool,
) -> None:
    """Update an existing Keycloak user with data from Excel.

    Args:
        keycloak_admin: The Keycloak admin client
        existing_user: The existing user dict from Keycloak
        user: The user data from Excel
        dry_run: If True, only log actions without executing them
    """
    existing_user_id = existing_user.get("id")
    existing_username = existing_user.get("username")

    # Get existing attributes
    existing_attributes = existing_user.get("attributes", {})
    existing_fullname = (
        existing_attributes.get("fullName", [None])[0]
        if existing_attributes.get("fullName")
        else None
    )
    existing_hometown = (
        existing_attributes.get("hometown", [None])[0]
        if existing_attributes.get("hometown")
        else None
    )
    existing_effective_date = (
        existing_attributes.get("effectiveDate", [None])[0]
        if existing_attributes.get("effectiveDate")
        else None
    )
    existing_expiration_date = (
        existing_attributes.get("expirationDate", [None])[0]
        if existing_attributes.get("expirationDate")
        else None
    )
    existing_discord = (
        existing_attributes.get("discord", [None])[0]
        if existing_attributes.get("discord")
        else None
    )
    existing_bricklink = (
        existing_attributes.get("bricklink", [None])[0]
        if existing_attributes.get("bricklink")
        else None
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
    if existing_effective_date != user.effectiveDate:
        changes.append(
            f"effectiveDate attribute: {existing_effective_date} → {user.effectiveDate}"
        )
    if existing_expiration_date != user.expirationDate:
        changes.append(
            f"expirationDate attribute: {existing_expiration_date} → {user.expirationDate}"
        )
    if existing_discord != user.discord:
        changes.append(f"discord attribute: {existing_discord} → {user.discord}")
    if existing_bricklink != user.bricklink:
        changes.append(f"bricklink attribute: {existing_bricklink} → {user.bricklink}")
    if not existing_first_name and user.firstName:
        changes.append(f"firstName: (empty) → {user.firstName}")
    if not existing_last_name and user.lastName:
        changes.append(f"lastName: (empty) → {user.lastName}")

    # Check if email is verified
    is_email_verified = existing_user.get("emailVerified", False)
    if not is_email_verified:
        logger.warning(
            f"User {existing_username} ({user.email}) has not verified their email."
        )

    if changes:
        message = f"Updating existing user {existing_username} ({user.email})..."
        if dry_run:
            click.echo(message)
            click.echo(f"  Changes: {', '.join(changes)}")
        else:
            logger.info(message)
            if existing_user_id:
                # Prepare attributes update
                attributes = existing_attributes.copy()
                if user.fullName:
                    attributes["fullName"] = [user.fullName]
                if user.hometown:
                    attributes["hometown"] = [user.hometown]
                if user.effectiveDate:
                    attributes["effectiveDate"] = [user.effectiveDate]
                if user.expirationDate:
                    attributes["expirationDate"] = [user.expirationDate]
                if user.discord:
                    attributes["discord"] = [user.discord]
                if user.bricklink:
                    attributes["bricklink"] = [user.bricklink]

                # Use existing firstName/lastName if present, otherwise use new from Excel
                update_payload = {
                    "email": user.email,
                    "firstName": final_first_name,
                    "lastName": final_last_name,
                    "attributes": attributes,
                }
                keycloak_admin.update_user(existing_user_id, update_payload)
    else:
        message = f"User {existing_username} ({user.email}) is already up-to-date"
        if dry_run:
            click.echo(message)
        else:
            logger.info(message)


def create_new_user(
    keycloak_admin: KeycloakAdmin,
    user: User,
    dry_run: bool,
) -> None:
    """Create a new Keycloak user with data from Excel.

    Sets a safe random password that is not meant to be remembered.
    This enables Keycloak to show the password dialog and allow sending
    a password reset email.

    Args:
        keycloak_admin: The Keycloak admin client
        user: The user data from Excel
        dry_run: If True, only log actions without executing them
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
        if user.effectiveDate:
            attributes["effectiveDate"] = [user.effectiveDate]
        if user.expirationDate:
            attributes["expirationDate"] = [user.expirationDate]
        if user.discord:
            attributes["discord"] = [user.discord]
        if user.bricklink:
            attributes["bricklink"] = [user.bricklink]

        new_user_id = keycloak_admin.create_user(
            {
                "username": user.username,
                "email": user.email,
                "emailVerified": False,
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
                        logger.info(f"Added user to group: {group_name}")
                    else:
                        logger.warning(f"Group not found: {group_name}")
                except KeycloakError as e:
                    logger.error(f"Error adding user to group {group_name}: {e}")


def disable_user(
    keycloak_admin: KeycloakAdmin,
    kc_user: dict[str, Any],
    dry_run: bool,
) -> None:
    """Disable a Keycloak user.

    Args:
        keycloak_admin: The Keycloak admin client
        kc_user: The Keycloak user dict
        dry_run: If True, only log actions without executing them
    """
    kc_username = kc_user.get("username")
    kc_email = kc_user.get("email")

    message = f"Disabling user {kc_username} ({kc_email})..."

    if dry_run:
        click.echo(message)
        click.echo(f"  Change: enabled: {kc_user.get('enabled', True)} → False")
    else:
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
    email: str | None,
) -> None:
    """Synchronize users from an Excel file to Keycloak using auto-detection."""
    click.echo(f"Synchronizing users from {excel_file}...")

    if email:
        click.echo(f"Filtering to only sync user with email: {email}")

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
    for user in excel_users:
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
                update_existing_user(keycloak_admin, existing_user, user, dry_run)
            else:
                create_new_user(keycloak_admin, user, dry_run)
        except KeycloakError as e:
            logger.error(f"Error syncing user {username} ({user.email}): {e}")

    # Disable users in Keycloak that are not in the Excel file
    # Skip this step if we're filtering by email (only syncing one specific user)
    if not email:
        excel_emails = [user.email for user in excel_users if user.email]
        for kc_user in keycloak_users:
            kc_username = kc_user.get("username")
            kc_email = kc_user.get("email")

            # Skip if user is in Excel file
            if kc_email and kc_email in excel_emails:
                continue

            # Skip if email is in protected list
            if kc_email and kc_email in PROTECTED_USERS:
                logger.info(f"Skipping protected user {kc_username} ({kc_email})")
                continue

            # Skip if username is "admin" (hardcoded protection)
            if kc_username == "admin":
                logger.info(f"Skipping admin user {kc_username}")
                continue

            # Disable the user
            if kc_email:
                disable_user(keycloak_admin, kc_user, dry_run)
