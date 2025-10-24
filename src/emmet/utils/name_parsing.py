"""Name parsing utilities."""

from typing import Optional
from typing import Tuple


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
