"""User schemas."""

import enum
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserType(enum.Enum):
    """Enum for user types"""

    COORDINATOR = "coordinator"
    STUDENT = "student"
    SOCIAL_WORKER = "social_worker"
    NTI = "nti"


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str
    user_type: UserType = Field(..., description="Type of user")
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(
        ..., min_length=8, description="User password (minimum 8 characters)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "full_name": "João Silva",
                "user_type": "student",
                "password": "securepassword123",
                "is_active": True,
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    user_type: Optional[UserType] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """User schema for responses."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "João Silva",
                "user_type": "student",
                "is_active": True,
                "created_at": "2025-09-19T10:30:00",
                "updated_at": "2025-09-19T10:30:00",
            }
        },
    )

    id: int
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    """Schema for authentication token response."""

    access_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    )


class TokenData(BaseModel):
    """Schema for token payload data."""

    email: Optional[str] = None
