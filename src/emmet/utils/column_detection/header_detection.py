"""Header row detection for Excel files."""

from openpyxl.worksheet.worksheet import Worksheet
import logging


logger = logging.getLogger(__name__)


def detect_header_row(ws: Worksheet) -> int:
    """
    Detect which row contains the header by looking for "bricklink" (case-insensitive).

    Returns the row number (1-based) of the header row.
    """
    # Check first 10 rows to find the header
    for row_num in range(1, min(11, (ws.max_row or 1) + 1)):
        row_values = [
            str(cell.value) if cell.value is not None else "" for cell in ws[row_num]
        ]

        # Check if any cell in this row contains "bricklink" (case-insensitive)
        for cell_value in row_values:
            if cell_value and "bricklink" in cell_value.lower():
                logger.info(
                    f"Detected header row at row {row_num} (contains 'bricklink')"
                )
                return row_num

    # Default to row 1 if no header detected
    logger.info("Using row 1 as header row (default)")
    return 1
