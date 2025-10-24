"""Date column detection for Excel files."""

from openpyxl.worksheet.worksheet import Worksheet
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
import logging
import re


logger = logging.getLogger(__name__)


def detect_date_columns(
    ws: Worksheet,
    header: List[str],
    skip_col_indices: List[int],
    header_row_num: int = 1,
) -> Tuple[Optional[int], Optional[int]]:
    """
    Detect which columns contain dates in dd.mm.yyyy format.

    Returns a tuple of (first_date_col_idx, second_date_col_idx).
    The first date is effectiveDate, the second is expirationDate.
    """
    # Pattern for dd.mm.yyyy format (as string or datetime)
    date_pattern = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")

    # Track which columns have date-like values
    column_date_counts: Dict[int, int] = {}

    # Start scanning after the header row
    data_start_row = header_row_num + 1
    for row in ws.iter_rows(
        min_row=data_start_row,
        max_row=min(data_start_row + 19, ws.max_row or data_start_row),
    ):  # Sample up to 20 data rows
        for col_idx, cell in enumerate(row):
            # Skip already identified columns
            if col_idx in skip_col_indices:
                continue

            if cell.value:
                # Check if it's a string matching date pattern
                if isinstance(cell.value, str) and date_pattern.match(
                    cell.value.strip()
                ):
                    column_date_counts[col_idx] = column_date_counts.get(col_idx, 0) + 1
                # Check if it's a datetime object from Excel
                elif hasattr(cell.value, "strftime"):
                    column_date_counts[col_idx] = column_date_counts.get(col_idx, 0) + 1

    # Get columns sorted by index that have date values
    date_columns = sorted(
        [col_idx for col_idx, count in column_date_counts.items() if count > 0]
    )

    effective_date_col = date_columns[0] if len(date_columns) >= 1 else None
    expiration_date_col = date_columns[1] if len(date_columns) >= 2 else None

    if effective_date_col is not None:
        logger.info(
            f"Detected effectiveDate column: '{header[effective_date_col]}' (index {effective_date_col})"
        )
    if expiration_date_col is not None:
        logger.info(
            f"Detected expirationDate column: '{header[expiration_date_col]}' (index {expiration_date_col})"
        )

    return effective_date_col, expiration_date_col
