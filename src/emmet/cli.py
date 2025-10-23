from emmet.constants import PROTECTED_USERS
from emmet.constants import REQUIRED_USER_ACTIONS
from emmet.types import User
from emmet.utils import parse_excel_users
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError
import click
import logging


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@click.group()
def main() -> None:
    """A CLI for synchronizing user data from an Excel file to Keycloak."""
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
    """Synchronize users from an Excel file to Keycloak."""
    click.echo(f"Synchronizing users from {excel_file}...")

    # Read users from Excel file
    excel_users: list[User] = parse_excel_users(excel_file)
    if not excel_users:
        logging.error(
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
            user_realm_name="master",
        )
        keycloak_admin.connection.get_token()
    except KeycloakError as e:
        logging.error(f"Error connecting to Keycloak: {e}")
        return

    # Get all users from Keycloak
    try:
        keycloak_users = keycloak_admin.get_users({})
        keycloak_usernames = [user["username"] for user in keycloak_users]
    except KeycloakError as e:
        logging.error(f"Error getting users from Keycloak: {e}")
        return

    # Sync users from Excel to Keycloak
    for user in excel_users:
        username = user.username
        if not username:
            logging.warning(f"Skipping user with missing username: {user}")
            continue

        try:
            user_id = keycloak_admin.get_user_id(username)
            if user_id:
                logging.info(f"Updating user {username}...")
                if not dry_run:
                    keycloak_admin.update_user(
                        user_id,
                        {
                            "email": user.email,
                            "firstName": user.firstName,
                            "lastName": user.lastName,
                        },
                    )
            else:
                logging.info(f"Creating user {username}...")
                if not dry_run:
                    keycloak_admin.create_user(
                        {
                            "username": username,
                            "email": user.email,
                            "firstName": user.firstName,
                            "lastName": user.lastName,
                            "enabled": True,
                            "requiredActions": REQUIRED_USER_ACTIONS,
                        }
                    )
        except KeycloakError as e:
            logging.error(f"Error syncing user {username}: {e}")

    # Disable users in Keycloak that are not in the Excel file
    excel_usernames = [user.username for user in excel_users]
    for username in keycloak_usernames:
        if username not in excel_usernames and username not in PROTECTED_USERS:
            logging.info(f"Disabling user {username}...")
            if not dry_run:
                try:
                    user_id = keycloak_admin.get_user_id(username)
                    if user_id:
                        keycloak_admin.update_user(user_id, {"enabled": False})
                except KeycloakError as e:
                    logging.error(f"Error disabling user {username}: {e}")


@main.command()
@click.argument("excel_file", type=click.Path(exists=True))
def dump_excel(excel_file: str) -> None:
    """Parse and dump data from an Excel file to visually confirm parsing."""
    click.echo(f"Parsing and dumping users from {excel_file}...")
    users: list[User] = parse_excel_users(excel_file)
    if users:
        for user in users:
            click.echo(user.model_dump_json(indent=2))
    else:
        click.echo("No users found or an error occurred during parsing.")


if __name__ == "__main__":
    main()
