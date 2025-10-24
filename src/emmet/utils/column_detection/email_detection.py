"""Email column detection for Excel files."""

from openpyxl.worksheet.worksheet import Worksheet
from typing import Dict
from typing import List
from typing import Optional
import logging
import re


logger = logging.getLogger(__name__)


def detect_email_column(
    ws: Worksheet, header: List[str], header_row_num: int = 1
) -> Optional[int]:
    """
    Detect which column contains email addresses by scanning the data.

    Returns the column index (0-based) or None if no email column is found.
    """
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # Count email matches per column
    column_email_counts: Dict[int, int] = {}

    # Start scanning after the header row
    data_start_row = header_row_num + 1
    for row in ws.iter_rows(
        min_row=data_start_row,
        max_row=min(data_start_row + 19, ws.max_row or data_start_row),
    ):  # Sample up to 20 data rows
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
