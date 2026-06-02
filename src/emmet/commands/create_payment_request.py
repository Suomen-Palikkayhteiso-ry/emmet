"""Create a manual payment request for one member."""

from emmet.types import User
from emmet.utils import parse_excel_users
from emmet.utils.payments import build_virtual_barcode
from emmet.utils.payments import format_amount
from emmet.utils.payments import format_reference
from emmet.utils.payments import format_rf_reference
from emmet.utils.payments import generate_member_reference
from emmet.utils.payments import generate_rf_reference
from emmet.utils.payments import normalize_iban
from emmet.utils.payments import parse_amount
from emmet.utils.payments import parse_due_date
from emmet.utils.payments import PaymentError
import click
import datetime
import logging


logger = logging.getLogger(__name__)


def _find_user_by_email(users: list[User], email: str) -> User:
    normalized_email = email.strip().lower()
    matches = [
        user
        for user in users
        if user.email is not None and str(user.email).lower() == normalized_email
    ]
    if not matches:
        raise click.ClickException(f"No member found with email: {email}")
    if len(matches) > 1:
        raise click.ClickException(f"Multiple members found with email: {email}")
    return matches[0]


def _resolve_barcode_version(requested_version: str, iban: str) -> int:
    if requested_version == "auto":
        return 4 if iban.startswith("FI") else 5
    return int(requested_version)


@click.command(name="create-payment-request")
@click.argument("excel_file", type=click.Path(exists=True))
@click.option(
    "--email", required=True, help="Create a payment request for this member email."
)
@click.option("--iban", required=True, help="Creditor IBAN.")
@click.option(
    "--amount", required=True, help="Payment amount in euros, for example 10 or 10.00."
)
@click.option(
    "--due-date", required=True, help="Payment due date in YYYY-MM-DD format."
)
@click.option(
    "--creditor-name",
    default="Suomen Palikkaharrastajat ry",
    show_default=True,
    help="Creditor name shown in the payment request.",
)
@click.option(
    "--barcode-version",
    type=click.Choice(["4", "5", "auto"]),
    default="auto",
    show_default=True,
    help="Finnish virtual barcode version to generate.",
)
def create_payment_request(
    excel_file: str,
    email: str,
    iban: str,
    amount: str,
    due_date: str,
    creditor_name: str,
    barcode_version: str,
) -> None:
    """Create payment details and a virtual barcode payload for one member."""
    users: list[User] = parse_excel_users(excel_file, None)
    if not users:
        logger.error(
            "No users found in the Excel file or an error occurred during parsing."
        )
        raise click.ClickException(
            "No users found in the Excel file or an error occurred during parsing."
        )

    user = _find_user_by_email(users, email)
    if user.excelRow is None:
        raise click.ClickException("Selected member does not have an Excel row number.")

    try:
        normalized_iban = normalize_iban(iban)
        euros, cents = parse_amount(amount)
        parsed_due_date = parse_due_date(due_date)
        version = _resolve_barcode_version(barcode_version, normalized_iban)
        payment_year = datetime.date.today().year
        reference = generate_member_reference(payment_year, user.excelRow)
        rf_reference = generate_rf_reference(reference)
        virtual_barcode = build_virtual_barcode(
            iban=normalized_iban,
            euros=euros,
            cents=cents,
            due_date=parsed_due_date,
            reference=reference,
            version=version,
        )
    except PaymentError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo("Payment request")
    click.echo(f"Creditor: {creditor_name}")
    click.echo(f"IBAN: {normalized_iban}")
    click.echo(f"Amount: {format_amount(euros, cents)} EUR")
    click.echo(f"Due date: {parsed_due_date.isoformat()}")
    click.echo("")
    click.echo(f"Member: {user.fullName or '-'}")
    click.echo(f"Email: {user.email}")
    click.echo(f"Excel row: {user.excelRow}")
    click.echo("")
    click.echo(f"Finnish reference: {format_reference(reference)}")
    if version == 5:
        click.echo(f"RF reference: {format_rf_reference(rf_reference)}")
    click.echo(f"Virtual barcode version: {version}")
    click.echo(f"Virtual barcode: {virtual_barcode}")
