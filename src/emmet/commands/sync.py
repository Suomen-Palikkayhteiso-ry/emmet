"""Sync command - synchronize users from Excel to Keycloak."""

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

    logger.info(f"Updating existing user {existing_username} ({user.email})...")

    if not dry_run and existing_user_id:
        update_payload = {
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName,
        }
        keycloak_admin.update_user(existing_user_id, update_payload)


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
    logger.info(f"Creating new user {user.username} ({user.email})...")

    if not dry_run:
        # Generate a secure random password (not meant to be remembered)
        # This allows Keycloak to show password dialog and send reset emails
        random_password = secrets.token_urlsafe(32)

        keycloak_admin.create_user(
            {
                "username": user.username,
                "email": user.email,
                "emailVerified": False,
                "firstName": user.firstName,
                "lastName": user.lastName,
                "enabled": True,
                "requiredActions": list(REQUIRED_USER_ACTIONS),
                "attributes": {"locale": ["fi"]},
                "credentials": [
                    {
                        "type": "password",
                        "value": random_password,
                        "temporary": True,
                    }
                ],
            }
        )


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

    logger.info(f"Disabling user {kc_username} ({kc_email})...")

    if not dry_run:
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
def sync(
    excel_file: str,
    keycloak_server: str,
    keycloak_realm: str,
    keycloak_client_id: str,
    keycloak_client_secret: str,
    dry_run: bool,
) -> None:
    """Synchronize users from an Excel file to Keycloak using auto-detection."""
    click.echo(f"Synchronizing users from {excel_file}...")

    # Read users from Excel file using auto-detection
    excel_users: list[User] = parse_excel_users(excel_file, None)
    if not excel_users:
        logger.error(
            "No users found in the Excel file or an error occurred during parsing."
        )
        return

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
