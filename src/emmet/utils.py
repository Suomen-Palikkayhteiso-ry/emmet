from emmet.types import ExcelColumnMapping
from emmet.types import User
from openpyxl import load_workbook
from typing import Any
from typing import cast
from typing import List
from typing import Optional
import logging


logger = logging.getLogger(__name__)


def parse_excel_users(
    file_path: str, column_mapping: Optional[ExcelColumnMapping] = None
) -> List[User]:
    users: List[User] = []
    if column_mapping is None:
        column_mapping = ExcelColumnMapping()  # Use default mapping

    try:
        wb = load_workbook(file_path)
        ws = wb.active
        if ws is None:
            logger.warning(f"Worksheet is empty in {file_path}")
            return []

        header = [str(cell.value) if cell.value is not None else "" for cell in ws[1]]

        # Create a reverse mapping for easier lookup
        reverse_mapping = {
            column_mapping.username: "username",
            column_mapping.email: "email",
            column_mapping.firstName: "firstName",
            column_mapping.lastName: "lastName",
        }

        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            user_data_raw = {header[i]: cell.value for i, cell in enumerate(row)}

            processed_user_data = {}
            for excel_col, user_field in reverse_mapping.items():
                value = user_data_raw.get(excel_col)
                if value is not None:
                    processed_user_data[user_field] = str(value)

            username_value = processed_user_data.get("username")
            if not username_value:
                logger.warning(
                    f"Skipping row {row_idx} due to missing username: {user_data_raw}"
                )
                continue

            try:
                user = User(**cast(dict[str, Any], processed_user_data))
                users.append(user)
            except Exception as e:
                logger.warning(
                    f"Skipping invalid user data in row {row_idx}: {processed_user_data}. Error: {e}"
                )
    except Exception as e:
        logger.error(f"Error reading Excel file {file_path}: {e}")
    return users
