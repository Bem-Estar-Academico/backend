"""User schemas."""

from typing import Optional
from datetime import datetime
from app.models.user import UserType
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, ValidationInfo


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str
    user_type: UserType = Field(..., description="Type of user")
    is_active: bool = True

    registration_number: Optional[str] = Field(
        None, description="Número de matrícula (apenas para estudantes)", max_length=20
    )
    cpf: Optional[str] = Field(
        None,
        description="CPF (apenas para estudantes)",
        max_length=14,
        pattern=r"^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$",
    )


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(
        ..., min_length=8, description="User password (minimum 8 characters)"
    )

    @field_validator("registration_number", "cpf")
    @classmethod
    def validate_student_fields(cls, value: Optional[str], validation_info: ValidationInfo):
        if value is not None and validation_info.data.get("user_type") != UserType.STUDENT:
            raise ValueError(
                "registration_number and cpf can only be provided for students"
            )
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "full_name": "João Silva",
                "user_type": "STUDENT",
                "password": "securepassword123",
                "is_active": True,
                "registration_number": "202301001",
                "cpf": "123.456.789-00",
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

    registration_number: Optional[str] = Field(
        None, description="Número de matrícula (apenas para estudantes)", max_length=20
    )
    cpf: Optional[str] = Field(
        None,
        description="CPF (apenas para estudantes)",
        max_length=14,
        pattern=r"^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$",
    )


class UserInfo(BaseModel):
    id: int
    email: str
    full_name: str
    user_type: UserType

    registration_number: Optional[str] = None
    cpf: Optional[str] = None

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
                "registration_number": "202301001",
                "cpf": "123.456.789-00",
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
