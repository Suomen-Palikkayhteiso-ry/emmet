"""Dump Excel command - parse and dump data from an Excel file."""

from emmet.types import User
from emmet.utils import parse_excel_users
import click


@click.command()
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
