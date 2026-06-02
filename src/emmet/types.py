from pydantic import BaseModel
from pydantic import EmailStr
from typing import Optional


class User(BaseModel):
    username: str
    excelRow: Optional[int] = None
    email: Optional[EmailStr] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    fullName: Optional[str] = None
    hometown: Optional[str] = None
    registrationDate: Optional[str] = None
    paymentDate: Optional[str] = None
    discord: Optional[str] = None
    bricklink: Optional[str] = None
    brickowl: Optional[str] = None
    noVotingRights: Optional[bool] = None
    phone: Optional[str] = None
