"""Column detection heuristics for Excel files.

This package is organized into separate modules per column type:
- header_detection: Detect header row location
- generic_detection: Generic column detection by name
- email_detection: Email column detection
- name_detection: Name column detection
- date_detection: Date column detection

All functions are re-exported from the main column_detection module for backward compatibility.
"""

from emmet.utils.column_detection.date_detection import detect_date_columns
from emmet.utils.column_detection.email_detection import detect_email_column
from emmet.utils.column_detection.generic_detection import detect_column_by_name
from emmet.utils.column_detection.header_detection import detect_header_row
from emmet.utils.column_detection.name_detection import detect_name_column


__all__ = [
    "detect_column_by_name",
    "detect_date_columns",
    "detect_email_column",
    "detect_header_row",
    "detect_name_column",
]
