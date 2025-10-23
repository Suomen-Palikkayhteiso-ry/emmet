from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from typing import Optional


class User(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None


class ExcelColumnMapping(BaseModel):
    username: str = Field("username", description="Excel column name for username")
    email: str = Field("email", description="Excel column name for email")
    firstName: str = Field("firstName", description="Excel column name for first name")
    lastName: str = Field("lastName", description="Excel column name for last name")
