from emmet.types import User
from openpyxl import load_workbook
from typing import Any
from typing import cast
from typing import List
import logging


logger = logging.getLogger(__name__)


def parse_excel_users(file_path: str) -> List[User]:
    users: List[User] = []
    try:
        wb = load_workbook(file_path)
        ws = wb.active
        if ws is None:
            return []
        header = [str(cell.value) for cell in ws[1]]
        for row in ws.iter_rows(min_row=2):
            user_data_raw = {header[i]: cell.value for i, cell in enumerate(row)}

            username_value_raw = user_data_raw.get("username")
            if username_value_raw is None:
                logger.warning(
                    f"Skipping user data due to missing username: {user_data_raw}"
                )
                continue

            # Explicitly assert type for mypy
            processed_username: str = str(username_value_raw)
            processed_email = (
                str(user_data_raw.get("email"))
                if user_data_raw.get("email") is not None
                else None
            )
            processed_firstName = (
                str(user_data_raw.get("firstName"))
                if user_data_raw.get("firstName") is not None
                else None
            )
            processed_lastName = (
                str(user_data_raw.get("lastName"))
                if user_data_raw.get("lastName") is not None
                else None
            )

            processed_user_data = {
                "username": processed_username,
                "email": processed_email,
                "firstName": processed_firstName,
                "lastName": processed_lastName,
            }

            try:
                user = User(**cast(dict[str, Any], processed_user_data))
                users.append(user)
            except Exception as e:
                logger.warning(
                    f"Skipping invalid user data: {processed_user_data}. Error: {e}"
                )
    except Exception as e:
        logger.error(f"Error reading Excel file {file_path}: {e}")
    return users
