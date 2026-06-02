"""Membership status helpers."""

from emmet.constants import PROTECTED_USERS
from emmet.types import User
import datetime
import re


def should_skip_special_email(email: str | None) -> bool:
    """Return True for protected/system emails that must be skipped."""
    if not email:
        return False

    normalized_email = email.strip().lower()

    if normalized_email in PROTECTED_USERS:
        return True

    if normalized_email == "palikkaharrastajatry@outlook.com":
        return True

    return (
        re.match(r"^palikkaharrastajatry\+[^@]+@outlook\.com$", normalized_email)
        is not None
    )


def parse_payment_date(value: str | None) -> datetime.date | None:
    """Parse common date formats used in payment date column."""
    if value is None:
        return None
    date_value = value.strip()
    if not date_value:
        return None

    for date_format in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(date_value, date_format).date()
        except ValueError:
            continue
    return None


def membership_valid_until(value: str | None) -> datetime.date | None:
    """Membership is valid through the end of year after the payment year."""
    payment_date = parse_payment_date(value)
    if payment_date is None:
        return None
    return datetime.date(payment_date.year + 1, 12, 31)


def is_membership_active(user: User, today: datetime.date | None = None) -> bool:
    """Return whether the user should be provisioned based on payment date."""
    valid_until = membership_valid_until(user.paymentDate)
    if valid_until is None:
        return False
    reference_date = today or datetime.date.today()
    return reference_date <= valid_until
