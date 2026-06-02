"""Payment reference and Finnish virtual barcode utilities."""

from decimal import Decimal
from decimal import InvalidOperation
from decimal import ROUND_HALF_UP
import datetime
import re


class PaymentError(ValueError):
    """Raised when payment details cannot be encoded safely."""


def normalize_iban(value: str) -> str:
    """Return an uppercase compact IBAN after validating its checksum."""
    iban = re.sub(r"\s+", "", value).upper()
    if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]+", iban):
        raise PaymentError(
            "IBAN must start with a country code and contain only letters and digits."
        )

    rearranged = iban[4:] + iban[:4]
    numeric = "".join(_iban_char_to_number(char) for char in rearranged)
    if _mod97(numeric) != 1:
        raise PaymentError("IBAN checksum is invalid.")
    return iban


def _iban_char_to_number(char: str) -> str:
    if char.isdigit():
        return char
    return str(ord(char) - ord("A") + 10)


def _mod97(value: str) -> int:
    remainder = 0
    for char in value:
        remainder = (remainder * 10 + int(char)) % 97
    return remainder


def calculate_finnish_reference(base: str) -> str:
    """Append the Finnish national reference checksum to a base number."""
    if not re.fullmatch(r"[1-9][0-9]{2,18}", base):
        raise PaymentError(
            "Reference base must be 3-19 digits and must not start with zero."
        )

    weights = [7, 3, 1]
    total = 0
    for index, digit in enumerate(reversed(base)):
        total += int(digit) * weights[index % len(weights)]
    check_digit = (10 - (total % 10)) % 10
    return f"{base}{check_digit}"


def generate_member_reference(year: int, excel_row: int) -> str:
    """Generate a Finnish reference from payment year and Excel row."""
    if year < 1:
        raise PaymentError("Payment year must be positive.")
    if excel_row < 1:
        raise PaymentError("Excel row must be positive.")
    return calculate_finnish_reference(f"{year}{excel_row}")


def format_reference(reference: str) -> str:
    """Format a reference number in five-digit groups from the right."""
    groups: list[str] = []
    remaining = reference
    while remaining:
        groups.append(remaining[-5:])
        remaining = remaining[:-5]
    return " ".join(reversed(groups))


def generate_rf_reference(reference: str) -> str:
    """Generate an RF creditor reference from a numeric reference."""
    compact_reference = reference.replace(" ", "")
    if not re.fullmatch(r"[0-9]{1,21}", compact_reference):
        raise PaymentError("RF reference source must contain 1-21 digits.")
    check_digits = 98 - _mod97(f"{compact_reference}271500")
    return f"RF{check_digits:02d}{compact_reference}"


def format_rf_reference(reference: str) -> str:
    """Format an RF reference in four-character groups."""
    compact_reference = reference.replace(" ", "").upper()
    groups = []
    for index in range(0, len(compact_reference), 4):
        groups.append(compact_reference[index:][:4])
    return " ".join(groups)


def parse_amount(value: str) -> tuple[int, int]:
    """Parse an amount as euro and cent fields for a virtual barcode."""
    normalized = value.strip().replace(",", ".")
    try:
        amount = Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise PaymentError("Amount must be a decimal euro value.") from exc

    if amount < Decimal("0"):
        raise PaymentError("Amount must not be negative.")
    if amount > Decimal("999999.99"):
        raise PaymentError(
            "Amount exceeds the virtual barcode maximum of 999999.99 EUR."
        )

    cents_total = int(amount * 100)
    return cents_total // 100, cents_total % 100


def format_amount(euros: int, cents: int) -> str:
    """Return a display amount with two decimals."""
    return f"{euros}.{cents:02d}"


def parse_due_date(value: str) -> datetime.date:
    """Parse the command due date format."""
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise PaymentError("Due date must be in YYYY-MM-DD format.") from exc


def build_virtual_barcode(
    *,
    iban: str,
    euros: int,
    cents: int,
    due_date: datetime.date,
    reference: str,
    version: int,
) -> str:
    """Build a Finnish virtual barcode payload for versions 4 and 5."""
    normalized_iban = normalize_iban(iban)
    account_field = _barcode_account_field(normalized_iban)
    amount_field = f"{euros:06d}{cents:02d}"
    due_date_field = due_date.strftime("%y%m%d")

    if version == 4:
        if not normalized_iban.startswith("FI"):
            raise PaymentError("Virtual barcode version 4 requires a FI IBAN.")
        reference_field = _national_reference_field(reference)
        return f"4{account_field}{amount_field}000{reference_field}{due_date_field}"

    if version == 5:
        rf_reference = generate_rf_reference(reference)
        reference_field = _rf_reference_field(rf_reference)
        return f"5{account_field}{amount_field}{reference_field}{due_date_field}"

    raise PaymentError("Barcode version must be 4 or 5.")


def _barcode_account_field(iban: str) -> str:
    account_field = iban[2:]
    if not re.fullmatch(r"[0-9]{16}", account_field):
        raise PaymentError(
            "Virtual barcode requires the IBAN without country code to be exactly 16 digits."
        )
    return account_field


def _national_reference_field(reference: str) -> str:
    compact_reference = reference.replace(" ", "")
    if not re.fullmatch(r"[0-9]{4,20}", compact_reference):
        raise PaymentError("Finnish reference must be 4-20 digits.")
    return compact_reference.zfill(20)


def _rf_reference_field(reference: str) -> str:
    compact_reference = reference.replace(" ", "").upper()
    if not compact_reference.startswith("RF"):
        raise PaymentError("RF reference must start with RF.")
    numeric_part = compact_reference[2:]
    if not re.fullmatch(r"[0-9]{4,23}", numeric_part):
        raise PaymentError("RF reference must contain only digits after RF.")
    check_digits = numeric_part[:2]
    reference_digits = numeric_part[2:]
    return f"{check_digits}{reference_digits.zfill(21)}"
