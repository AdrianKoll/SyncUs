from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from ..models.enums import Gender


class UserBase(BaseModel):
    name: str
    email: EmailStr
    gender: Optional[Gender] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    gender: Optional[Gender] = None
    password: Optional[str] = None
    current_password: Optional[str] = None


class User(UserBase):
    id: int
    room_id: Optional[int] = None
    connection_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
