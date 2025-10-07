"""User schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserType


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
                "user_type": "STUDENT",
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


class UserInfo(BaseModel):
    id: int
    email: str
    full_name: str
    user_type: UserType

    @classmethod
    def from_model(cls, user_model) -> "UserInfo":
        return cls(
            id=user_model.id,
            email=user_model.email,
            full_name=user_model.full_name,
            user_type=user_model.user_type,
        )

    model_config = ConfigDict(from_attributes=True)


class User(UserBase):
    """User schema for responses."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "João Silva",
                "user_type": "STUDENT",
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
