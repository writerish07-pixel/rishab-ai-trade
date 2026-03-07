from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    angel_one_api_key: Optional[str] = None
    angel_one_client_id: Optional[str] = None
    angel_one_password: Optional[str] = None
    angel_one_totp_secret: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    is_admin: bool
    angel_one_client_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AngelOneConnect(BaseModel):
    api_key: str
    client_id: str
    password: str
    totp_secret: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[int] = None
