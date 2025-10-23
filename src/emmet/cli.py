from emmet.constants import PROTECTED_USERS
from emmet.constants import REQUIRED_USER_ACTIONS
from emmet.types import User
from emmet.utils import parse_excel_users
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError
import click
import logging


logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging (show warnings and info messages).",
)
def main(verbose: bool) -> None:
    """A CLI for synchronizing user data from an Excel file to Keycloak."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")
    pass


@main.command()
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
                # Update existing user
                existing_user_id = existing_user.get("id")
                existing_username = existing_user.get("username")
                email_verified = existing_user.get("emailVerified", False)
                logger.info(
                    f"Updating existing user {existing_username} ({user.email})..."
                )
                if not dry_run:
                    update_payload = {
                        "email": user.email,
                        "firstName": user.firstName,
                        "lastName": user.lastName,
                    }
                    keycloak_admin.update_user(existing_user_id, update_payload)
                    # Send verification email if email is not verified
                    if not email_verified:
                        try:
                            # Update user to set emailVerified=False
                            keycloak_admin.update_user(
                                existing_user_id, {"emailVerified": False}
                            )
                            # Send verification email which automatically adds VERIFY_EMAIL to required actions
                            keycloak_admin.send_verify_email(user_id=existing_user_id)
                            logger.info(
                                f"Sent verification email to {existing_username} ({user.email})"
                            )
                        except KeycloakError as e:
                            logger.warning(
                                f"Failed to send verification email to {existing_username}: {e}"
                            )
            else:
                # Create new user with UUID4 username
                logger.info(f"Creating new user {username} ({user.email})...")
                if not dry_run:
                    user_id = keycloak_admin.create_user(
                        {
                            "username": username,
                            "email": user.email,
                            "emailVerified": False,
                            "firstName": user.firstName,
                            "lastName": user.lastName,
                            "enabled": True,
                            "requiredActions": list(REQUIRED_USER_ACTIONS),
                        }
                    )
                    # Send verification email for new users
                    try:
                        keycloak_admin.send_verify_email(user_id=user_id)
                        logger.info(
                            f"Sent verification email to {username} ({user.email})"
                        )
                    except KeycloakError as e:
                        logger.warning(
                            f"Failed to send verification email to {username}: {e}"
                        )
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
            logger.info(f"Disabling user {kc_username} ({kc_email})...")
            if not dry_run:
                try:
                    user_id = kc_user.get("id")
                    if user_id:
                        keycloak_admin.update_user(user_id, {"enabled": False})
                except KeycloakError as e:
                    logger.error(f"Error disabling user {kc_username}: {e}")


@main.command()
@click.argument("excel_file", type=click.Path(exists=True))
def dump_excel(excel_file: str) -> None:
    """Parse and dump data from an Excel file using auto-detection."""
    click.echo(f"Parsing and dumping users from {excel_file}...")

    # Use auto-detection
    users: list[User] = parse_excel_users(excel_file, None)
    if users:
        for user in users:
            click.echo(user.model_dump_json(indent=2))
    else:
        click.echo("No users found or an error occurred during parsing.")


if __name__ == "__main__":
    main()
