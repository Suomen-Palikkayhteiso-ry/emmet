from pydantic import BaseModel
from pydantic import EmailStr
from typing import Optional


class User(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    fullName: Optional[str] = None
    hometown: Optional[str] = None
    effectiveDate: Optional[str] = None
    expirationDate: Optional[str] = None
    discord: Optional[str] = None
    bricklink: Optional[str] = None
