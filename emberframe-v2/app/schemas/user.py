"""
User schemas
"""

from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    storage_quota: int
    storage_used: int
    theme: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserPreferences(BaseModel):
    theme: Optional[str] = "ember-blue"
    notifications_enabled: Optional[bool] = True
    desktop_layout: Optional[dict] = {}
    shortcuts: Optional[dict] = {}
