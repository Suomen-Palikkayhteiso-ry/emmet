"""Verify ID token command - verify and display ID token contents."""

from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakError
import click
import json
import logging


logger = logging.getLogger(__name__)


@click.command()
@click.argument("token")
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
    required=False,
    help="Keycloak client secret (if required).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "pretty"], case_sensitive=False),
    default="pretty",
    help="Output format: json or pretty.",
)
def verify_token(
    token: str,
    keycloak_server: str,
    keycloak_realm: str,
    keycloak_client_id: str,
    keycloak_client_secret: str | None,
    output_format: str,
) -> None:
    """Verify and display the contents of an ID token.

    TOKEN should be the JWT token string to verify.
    """
    try:
        # Initialize Keycloak OpenID client
        keycloak_openid = KeycloakOpenID(
            server_url=keycloak_server,
            client_id=keycloak_client_id,
            realm_name=keycloak_realm,
            client_secret_key=keycloak_client_secret,
        )

        # Decode and verify the token
        try:
            token_info = keycloak_openid.decode_token(
                token,
                validate=True,
            )
        except KeycloakError as e:
            logger.error(f"Token verification failed: {e}")
            click.echo(f"✗ Token verification failed: {e}", err=True)
            return

        # Get user info if token is valid
        try:
            userinfo = keycloak_openid.userinfo(token)
        except KeycloakError as e:
            logger.warning(f"Could not fetch userinfo: {e}")
            userinfo = None

        # Display token contents
        if output_format == "json":
            output = {
                "token_info": token_info,
                "userinfo": userinfo,
            }
            click.echo(json.dumps(output, indent=2, default=str))
        else:
            click.echo("✓ Token verified successfully!\n")
            click.echo("=" * 60)
            click.echo("TOKEN CLAIMS:")
            click.echo("=" * 60)

            # Display key claims
            key_claims = [
                ("Subject (User ID)", "sub"),
                ("Email", "email"),
                ("Email Verified", "email_verified"),
                ("Preferred Username", "preferred_username"),
                ("Name", "name"),
                ("Given Name", "given_name"),
                ("Family Name", "family_name"),
                ("Issued At", "iat"),
                ("Expiration", "exp"),
                ("Not Before", "nbf"),
                ("Issuer", "iss"),
                ("Audience", "aud"),
                ("Token Type", "typ"),
                ("Session State", "session_state"),
            ]

            for label, claim in key_claims:
                if claim in token_info:
                    value = token_info[claim]
                    # Format timestamps
                    if claim in ["iat", "exp", "nbf"]:
                        from datetime import datetime

                        dt = datetime.fromtimestamp(value)
                        value = f"{value} ({dt.isoformat()})"
                    click.echo(f"{label:25}: {value}")

            # Display other claims
            other_claims = {
                k: v
                for k, v in token_info.items()
                if k not in [c[1] for c in key_claims]
            }
            if other_claims:
                click.echo("\n" + "=" * 60)
                click.echo("OTHER CLAIMS:")
                click.echo("=" * 60)
                for key, value in sorted(other_claims.items()):
                    click.echo(f"{key:25}: {value}")

            # Display userinfo if available
            if userinfo:
                click.echo("\n" + "=" * 60)
                click.echo("USERINFO ENDPOINT DATA:")
                click.echo("=" * 60)
                for key, value in sorted(userinfo.items()):
                    click.echo(f"{key:25}: {value}")

        logger.info("Token verified successfully")

    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        click.echo(f"✗ Error: {e}", err=True)
