"""CLI for synchronizing user data from an Excel file to Keycloak."""

from emmet.commands import dump_excel
from emmet.commands import send_verification
from emmet.commands import sync
import click
import logging


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


# Register commands
main.add_command(sync)
main.add_command(dump_excel)
main.add_command(send_verification)


if __name__ == "__main__":
    main()
