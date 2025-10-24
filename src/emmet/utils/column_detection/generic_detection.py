"""Generic column detection by header name."""

from typing import List
from typing import Optional
import logging


logger = logging.getLogger(__name__)


def detect_column_by_name(header: List[str], search_term: str) -> Optional[int]:
    """
    Detect a column by searching for a case-insensitive term in the header.

    Returns the column index (0-based) or None if not found.
    """
    search_term_lower = search_term.lower()
    logger.info(f"Searching for column containing '{search_term}'...")
    for col_idx, header_value in enumerate(header):
        if header_value:
            logger.debug(f"  Checking column {col_idx}: '{header_value}'")
            if search_term_lower in header_value.lower():
                logger.info(
                    f"Detected {search_term} column: '{header[col_idx]}' (index {col_idx})"
                )
                return col_idx
    logger.warning(f"No column found containing '{search_term}'")
    return None
