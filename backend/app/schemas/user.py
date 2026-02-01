"""User and authentication schemas"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# Base schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)
    role: str = Field(default="viewer", pattern="^(admin|operator|viewer)$")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, pattern="^(admin|operator|viewer)$")
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int


# Authentication schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# API Key schemas
class APIKeyBase(BaseModel):
    name: str = Field(..., max_length=100)
    scopes: Optional[List[str]] = None


class APIKeyCreate(APIKeyBase):
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(APIKeyBase):
    id: int
    key_prefix: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyCreatedResponse(APIKeyResponse):
    """Response when creating a new API key - includes the full key"""
    key: str  # Full key, only shown once on creation


class APIKeyListResponse(BaseModel):
    items: List[APIKeyResponse]
    total: int
