"""List active member email addresses from Excel."""

from emmet.types import User
from emmet.utils import parse_excel_users
from emmet.utils.membership import is_membership_active
from emmet.utils.membership import parse_payment_date
from emmet.utils.membership import should_skip_special_email
import click
import datetime
import logging


logger = logging.getLogger(__name__)


def has_current_year_payment(user: User, today: datetime.date) -> bool:
    """Return whether the member paid the membership fee during today's year."""
    payment_date = parse_payment_date(user.paymentDate)
    return payment_date is not None and payment_date.year == today.year


@click.command(name="list-emails")
@click.argument("excel_file", type=click.Path(exists=True))
@click.option(
    "--without-current-year-payment",
    is_flag=True,
    help="Exclude active members who have paid the membership fee during the ongoing year.",
)
@click.option(
    "--with-current-year-payment",
    is_flag=True,
    help="Only include active members who have paid the membership fee during the ongoing year.",
)
def list_emails(
    excel_file: str,
    without_current_year_payment: bool,
    with_current_year_payment: bool,
) -> None:
    """Print email addresses of active members from an Excel file."""
    if without_current_year_payment and with_current_year_payment:
        raise click.UsageError(
            "Options --without-current-year-payment and "
            "--with-current-year-payment are mutually exclusive."
        )

    excel_users: list[User] = parse_excel_users(excel_file, None)
    if not excel_users:
        logger.error(
            "No users found in the Excel file or an error occurred during parsing."
        )
        return

    today = datetime.date.today()
    for user in excel_users:
        if user.email is None:
            continue
        email = str(user.email)
        if should_skip_special_email(email) or not is_membership_active(user, today):
            continue

        paid_this_year = has_current_year_payment(user, today)
        if without_current_year_payment and paid_this_year:
            continue
        if with_current_year_payment and not paid_this_year:
            continue

        click.echo(email)
