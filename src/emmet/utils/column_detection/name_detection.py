"""Name column detection for Excel files."""

from openpyxl.worksheet.worksheet import Worksheet
from typing import Dict
from typing import List
from typing import Optional
import logging
import re


logger = logging.getLogger(__name__)


def detect_name_column(
    ws: Worksheet,
    header: List[str],
    email_col_idx: Optional[int],
    header_row_num: int = 1,
) -> Optional[int]:
    """
    Detect which column contains full names (two or more words: first_name [middle_name(s)] last_name).

    Returns the column index (0-based) or None if no name column is found.
    """
    two_or_more_word_pattern = re.compile(r"^\s*\S+\s+\S+.*$")

    # Count two-or-more-word matches per column
    column_name_counts: Dict[int, int] = {}

    # Start scanning after the header row
    data_start_row = header_row_num + 1
    for row in ws.iter_rows(
        min_row=data_start_row,
        max_row=min(data_start_row + 19, ws.max_row or data_start_row),
    ):  # Sample up to 20 data rows
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
