from emmet.types import User
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
import logging
import re
import uuid


logger = logging.getLogger(__name__)


def detect_email_column(ws: Worksheet, header: List[str]) -> Optional[int]:
    """
    Detect which column contains email addresses by scanning the data.

    Returns the column index (0-based) or None if no email column is found.
    """
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # Count email matches per column
    column_email_counts: Dict[int, int] = {}

    for row in ws.iter_rows(
        min_row=2, max_row=min(20, ws.max_row or 2)
    ):  # Sample first 20 rows
        for col_idx, cell in enumerate(row):
            if cell.value and isinstance(cell.value, str):
                if email_pattern.match(cell.value.strip()):
                    column_email_counts[col_idx] = (
                        column_email_counts.get(col_idx, 0) + 1
                    )

    # Return column with most email matches (at least 1)
    if column_email_counts:
        email_col_idx = max(column_email_counts, key=lambda k: column_email_counts[k])
        logger.info(
            f"Detected email column: '{header[email_col_idx]}' (index {email_col_idx})"
        )
        return email_col_idx

    return None


def detect_name_column(
    ws: Worksheet, header: List[str], email_col_idx: Optional[int]
) -> Optional[int]:
    """
    Detect which column contains full names (two or more words: first_name [middle_name(s)] last_name).

    Returns the column index (0-based) or None if no name column is found.
    """
    two_or_more_word_pattern = re.compile(r"^\s*\S+\s+\S+.*$")

    # Count two-or-more-word matches per column
    column_name_counts: Dict[int, int] = {}

    for row in ws.iter_rows(
        min_row=2, max_row=min(20, ws.max_row or 2)
    ):  # Sample first 20 rows
        for col_idx, cell in enumerate(row):
            # Skip the email column
            if col_idx == email_col_idx:
                continue

            if cell.value and isinstance(cell.value, str):
                if two_or_more_word_pattern.match(cell.value.strip()):
                    column_name_counts[col_idx] = column_name_counts.get(col_idx, 0) + 1

    # Return column with most two-or-more-word matches (at least 1)
    if column_name_counts:
        name_col_idx = max(column_name_counts, key=lambda k: column_name_counts[k])
        logger.info(
            f"Detected name column: '{header[name_col_idx]}' (index {name_col_idx})"
        )
        return name_col_idx

    return None


def should_skip_row(row: Any) -> bool:
    """
    Check if a row should be skipped based on the presence of 'eronnut' (case-insensitive).

    Returns True if the row should be skipped, False otherwise.
    """
    for cell in row:
        if cell.value and isinstance(cell.value, str):
            if "eronnut" in cell.value.lower():
                return True
    return False


def parse_name_field(name_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a name string into first_name and last_name.

    - If the name has two or more parts: first part is first_name, last part is last_name
    - Middle parts are ignored
    - If only one part: it becomes first_name, last_name is None

    Returns (first_name, last_name) tuple.
    """
    if not name_str:
        return None, None

    parts = name_str.strip().split()  # Split on whitespace
    if len(parts) >= 2:
        return parts[0], parts[-1]  # First and last part
    elif len(parts) == 1:
        return parts[0], None

    return None, None


def parse_excel_users(
    file_path: str, _column_mapping: Optional[Any] = None
) -> List[User]:
    """
    Parse users from an Excel file using auto-detection heuristics.

    - Finds email column by scanning for email addresses
    - Finds name column by looking for cells with two words (first_name last_name)
    - Generates UUID4 username for each user
    - Skips rows containing 'eronnut' (case-insensitive)
    """
    users: List[User] = []

    try:
        wb = load_workbook(file_path)
        ws = wb.active
        if ws is None:
            logger.warning(f"Worksheet is empty in {file_path}")
            return []

        header = [str(cell.value) if cell.value is not None else "" for cell in ws[1]]

        # Use heuristic approach to detect columns
        email_col_idx = detect_email_column(ws, header)
        if email_col_idx is None:
            logger.error("Could not detect email column in Excel file")
            return []

        name_col_idx = detect_name_column(ws, header, email_col_idx)

        # Hometown is always the next column after name
        hometown_col_idx = (name_col_idx + 1) if name_col_idx is not None else None

        logger.info(
            f"Using heuristic parsing: email column at index {email_col_idx}, "
            f"name column at index {name_col_idx}, hometown column at index {hometown_col_idx}"
        )

        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            # Skip rows containing 'eronnut'
            if should_skip_row(row):
                logger.info(f"Skipping row {row_idx}: contains 'eronnut'")
                continue

            # Extract email
            email_cell = row[email_col_idx] if email_col_idx < len(row) else None
            email = (
                str(email_cell.value).strip()
                if email_cell and email_cell.value
                else None
            )

            if not email:
                logger.warning(f"Skipping row {row_idx}: no email found")
                continue

            # Extract and parse name
            first_name = None
            last_name = None
            full_name = None
            if name_col_idx is not None and name_col_idx < len(row):
                name_cell = row[name_col_idx]
                if name_cell and name_cell.value:
                    full_name = str(name_cell.value).strip()
                    first_name, last_name = parse_name_field(full_name)

            # Extract hometown (next column after name)
            hometown = None
            if hometown_col_idx is not None and hometown_col_idx < len(row):
                hometown_cell = row[hometown_col_idx]
                if hometown_cell and hometown_cell.value:
                    hometown = str(hometown_cell.value).strip()

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
