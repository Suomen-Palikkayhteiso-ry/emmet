"""Utility functions for the emmet package.

This package is organized into logical submodules:
- column_detection: Heuristics for detecting columns in Excel files
- name_parsing: Name parsing utilities
- excel_parsing: Excel file parsing and user extraction

All functions are re-exported from the main utils module for backward compatibility.
"""

# Re-export all functions from submodules for backward compatibility
from emmet.utils.column_detection import detect_column_by_name
from emmet.utils.column_detection import detect_date_columns
from emmet.utils.column_detection import detect_email_column
from emmet.utils.column_detection import detect_header_row
from emmet.utils.column_detection import detect_name_column
from emmet.utils.excel_parsing import parse_excel_users
from emmet.utils.excel_parsing import should_skip_row
from emmet.utils.name_parsing import parse_name_field


__all__ = [
    # Column detection
    "detect_column_by_name",
    "detect_date_columns",
    "detect_email_column",
    "detect_header_row",
    "detect_name_column",
    # Excel parsing
    "parse_excel_users",
    "should_skip_row",
    # Name parsing
    "parse_name_field",
]
