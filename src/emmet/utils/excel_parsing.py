"""Excel file parsing utilities."""

from emmet.types import User
from emmet.utils.column_detection import detect_date_columns
from emmet.utils.column_detection import detect_email_column
from emmet.utils.column_detection import detect_header_row
from emmet.utils.column_detection import detect_name_column
from emmet.utils.name_parsing import parse_name_field
from openpyxl import load_workbook
from typing import Any
from typing import List
from typing import Optional
import datetime
import logging
import unicodedata
import uuid


logger = logging.getLogger(__name__)


def normalize_header(value: str) -> str:
    """Normalize a header or string for accent-insensitive comparisons."""
    normalized = unicodedata.normalize("NFKD", value)
    without_diacritics = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return "".join(
        char for char in without_diacritics.lower().strip() if char.isalnum()
    )


def find_column_by_aliases(header: List[str], aliases: List[str]) -> Optional[int]:
    """Find a column index by matching accent-insensitive aliases in headers."""
    normalized_aliases = [normalize_header(alias) for alias in aliases if alias]
    for col_idx, header_value in enumerate(header):
        normalized_header = normalize_header(header_value)
        if not normalized_header:
            continue
        for alias in normalized_aliases:
            if alias and alias in normalized_header:
                return col_idx
    return None


def get_cell_value(row: Any, col_idx: Optional[int]) -> Any:
    """Safely get a cell value from a row by column index."""
    if col_idx is None or col_idx < 0 or col_idx >= len(row):
        return None
    return row[col_idx].value


def get_string_cell_value(row: Any, col_idx: Optional[int]) -> Optional[str]:
    """Get a trimmed string value from a row/column pair."""
    value = get_cell_value(row, col_idx)
    if value is None:
        return None
    value_str = str(value).strip()
    return value_str if value_str else None


def format_date_cell(value: Any) -> Optional[str]:
    """Format an Excel date-like value as dd.mm.yyyy when possible."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, datetime.date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def parse_boolean_cell(value: Any) -> Optional[bool]:
    """Parse common spreadsheet boolean values."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, float):
        if value == 1.0:
            return True
        if value == 0.0:
            return False
        return None
    if isinstance(value, str):
        normalized = normalize_header(value)
        if normalized in {"true", "1", "yes", "y", "kylla", "x"}:
            return True
        if normalized in {"false", "0", "no", "n", "ei"}:
            return False
    return None


def should_skip_row(row: Any, resigned_col_idx: Optional[int] = None) -> bool:
    """
    Check if a row should be skipped based on resigned status.

    Returns True if:
    - the explicit 'Eronnut' boolean column is true, or
    - any string cell contains 'eronnut' (case-insensitive).
    Returns True if the row should be skipped, False otherwise.
    """
    resigned_value = parse_boolean_cell(get_cell_value(row, resigned_col_idx))
    if resigned_value is True:
        return True

    for cell in row:
        if cell.value and isinstance(cell.value, str):
            if "eronnut" in cell.value.lower():
                return True
    return False


def parse_excel_users(
    file_path: str, _column_mapping: Optional[Any] = None
) -> List[User]:
    """
    Parse users from an Excel file.

    - Prefers known Finnish headers and falls back to heuristics when needed
    - Generates UUID4 username for each user
    - Skips rows marked as resigned ('Eronnut')
    """
    users: List[User] = []

    try:
        wb = load_workbook(file_path)
        ws = wb.active
        if ws is None:
            logger.warning(f"Worksheet is empty in {file_path}")
            return []

        # Detect which row contains the headers
        header_row_num = detect_header_row(ws)
        header = [
            str(cell.value) if cell.value is not None else ""
            for cell in ws[header_row_num]
        ]

        # Prefer explicit Finnish headers, then fall back to heuristics
        name_col_idx = find_column_by_aliases(header, ["nimi", "name"])
        hometown_col_idx = find_column_by_aliases(
            header, ["kotikaupunki", "hometown", "city"]
        )
        discord_col_idx = find_column_by_aliases(header, ["discord"])
        bricklink_col_idx = find_column_by_aliases(header, ["bricklink"])
        brickowl_col_idx = find_column_by_aliases(header, ["brickowl"])
        registration_date_col_idx = find_column_by_aliases(
            header, ["liittymispäivä", "liittymispaiva", "joined", "join date"]
        )
        payment_date_col_idx = find_column_by_aliases(
            header,
            [
                "jäsenmaksu",
                "jasenmaksu",
                "membership payment",
                "membership fee",
                "last payment",
            ],
        )
        no_voting_rights_col_idx = find_column_by_aliases(
            header, ["ei äänioikeutta", "ei aanioikeutta", "no voting rights"]
        )
        resigned_col_idx = find_column_by_aliases(header, ["eronnut", "resigned"])
        email_col_idx = find_column_by_aliases(
            header, ["sähköposti", "sahkoposti", "email"]
        )
        phone_col_idx = find_column_by_aliases(header, ["puhelin", "phone"])

        if email_col_idx is None:
            email_col_idx = detect_email_column(ws, header, header_row_num)
        if email_col_idx is None:
            logger.error("Could not detect email column in Excel file")
            return []

        if name_col_idx is None:
            name_col_idx = detect_name_column(ws, header, email_col_idx, header_row_num)

        # Hometown fallback: next column after name if no explicit header found
        if hometown_col_idx is None and name_col_idx is not None:
            hometown_col_idx = name_col_idx + 1

        # Date fallbacks for older sheets
        skip_cols = [
            col
            for col in [email_col_idx, name_col_idx, hometown_col_idx]
            if col is not None
        ]
        first_date_col_idx, second_date_col_idx = detect_date_columns(
            ws, header, skip_cols, header_row_num
        )

        if registration_date_col_idx is None:
            registration_date_col_idx = first_date_col_idx
        if payment_date_col_idx is None:
            payment_date_col_idx = second_date_col_idx

        logger.info(
            f"Using parsing: email={email_col_idx}, name={name_col_idx}, hometown={hometown_col_idx}, "
            f"registrationDate={registration_date_col_idx}, paymentDate={payment_date_col_idx}, "
            f"discord column at index {discord_col_idx}, "
            f"bricklink column at index {bricklink_col_idx}, brickowl={brickowl_col_idx}, "
            f"noVotingRights={no_voting_rights_col_idx}, resigned={resigned_col_idx}, phone={phone_col_idx}"
        )

        # Start processing rows after the header row
        data_start_row = header_row_num + 1
        for row_idx, row in enumerate(
            ws.iter_rows(min_row=data_start_row), start=data_start_row
        ):
            # Skip rows marked as resigned
            if should_skip_row(row, resigned_col_idx):
                logger.info(f"Skipping row {row_idx}: marked as resigned")
                continue

            # Extract email
            email = get_string_cell_value(row, email_col_idx)

            if not email:
                logger.warning(f"Skipping row {row_idx}: no email found")
                continue

            # Extract and parse name
            first_name = None
            last_name = None
            full_name = None
            full_name = get_string_cell_value(row, name_col_idx)
            if full_name:
                first_name, last_name = parse_name_field(full_name)

            hometown = get_string_cell_value(row, hometown_col_idx)
            discord = get_string_cell_value(row, discord_col_idx)
            bricklink = get_string_cell_value(row, bricklink_col_idx)
            brickowl = get_string_cell_value(row, brickowl_col_idx)
            phone = get_string_cell_value(row, phone_col_idx)

            registration_date = format_date_cell(
                get_cell_value(row, registration_date_col_idx)
            )
            payment_date = format_date_cell(get_cell_value(row, payment_date_col_idx))
            no_voting_rights = parse_boolean_cell(
                get_cell_value(row, no_voting_rights_col_idx)
            )

            # Generate UUID4 username for new users
            username = str(uuid.uuid4())

            try:
                user = User(
                    username=username,
                    email=email,
                    firstName=first_name,
                    lastName=last_name,
                    fullName=full_name,
                    hometown=hometown,
                    registrationDate=registration_date,
                    paymentDate=payment_date,
                    discord=discord,
                    bricklink=bricklink,
                    brickowl=brickowl,
                    noVotingRights=no_voting_rights,
                    phone=phone,
                )
                users.append(user)
                logger.info(f"Parsed user from row {row_idx}: {email} -> {username}")
            except Exception as e:
                logger.warning(
                    f"Skipping invalid user data in row {row_idx}: email={email}, "
                    f"firstName={first_name}, lastName={last_name}. Error: {e}"
                )
    except Exception as e:
        logger.error(f"Error reading Excel file {file_path}: {e}")
    return users
