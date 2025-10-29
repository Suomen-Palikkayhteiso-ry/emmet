"""Set all emails verified command - set all users' emails as verified."""

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError
import click
import logging


logger = logging.getLogger(__name__)


@click.command()
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
def set_all_emails_verified(
    keycloak_server: str,
    keycloak_realm: str,
    keycloak_client_id: str,
    keycloak_client_secret: str,
) -> None:
    """Set all users' emails as verified."""
    click.echo("Setting all emails as verified...")

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

    # Get all users
    try:
        users = keycloak_admin.get_users({})
        if not users:
            logger.info("No users found in Keycloak.")
            return

        for user in users:
            user_id = user.get("id")
            username = user.get("username")
            email = user.get("email")

            if not user_id:
                logger.warning(f"User {username} has no ID, skipping.")
                continue

            # Set emailVerified to True
            try:
                keycloak_admin.update_user(
                    user_id=user_id, payload={"emailVerified": True}
                )
                logger.info(f"Email set as verified for {username} ({email})")
            except KeycloakError as e:
                logger.error(
                    f"Error setting email as verified for {username} ({email}): {e}"
                )

        click.echo("✓ All emails set as verified.")

    except KeycloakError as e:
        logger.error(f"Error getting users from Keycloak: {e}")
        return
