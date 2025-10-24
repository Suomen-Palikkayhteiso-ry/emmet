"""Send verification command - send verification email to a user."""

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError
import click
import logging


logger = logging.getLogger(__name__)


@click.command()
@click.argument("email")
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
def send_verification(
    email: str,
    keycloak_server: str,
    keycloak_realm: str,
    keycloak_client_id: str,
    keycloak_client_secret: str,
) -> None:
    """Send verification email to a specific user by email address."""
    click.echo(f"Sending verification email to {email}...")

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

    # Find user by email
    try:
        users = keycloak_admin.get_users({"email": email})
        if not users:
            logger.error(f"No user found with email: {email}")
            return

        if len(users) > 1:
            logger.warning(
                f"Multiple users found with email {email}, using the first one"
            )

        user = users[0]
        user_id = user.get("id")
        username = user.get("username")

        if not user_id:
            logger.error(f"User {email} has no ID")
            return

        # Set emailVerified to False
        keycloak_admin.update_user(user_id, {"emailVerified": False})

        # Send verification email
        keycloak_admin.send_verify_email(user_id=user_id)
        logger.info(f"Verification email sent to {username} ({email})")
        click.echo(f"✓ Verification email sent to {username} ({email})")

    except KeycloakError as e:
        logger.error(f"Error sending verification email to {email}: {e}")
        return
