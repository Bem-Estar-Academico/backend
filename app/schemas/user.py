"""Module for defining Pydantic schemas for user-related data."""

"""
This module defines various Pydantic schemas used for validating and serializing
user-related data throughout the application. It includes schemas for base user
information, user creation, user updates, user responses, and authentication tokens.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
)

from app.models.user import UserType


class UserBase(BaseModel):
    """
    Base schema for user data.

    Attributes:
        email (EmailStr): The user's email address, which must be unique.
        full_name (str): The full name of the user.
        user_type (UserType): The type of user (e.g., STUDENT, COORDINATOR, SOCIAL_WORKER, NTI).
        is_active (bool): Indicates if the user account is active. Defaults to True.
        registration_number (Optional[str]): The student's registration number, applicable only for students.
        cpf (Optional[str]): The student's CPF, applicable only for students.
    """

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
    """
    Schema for creating a new user.

    Extends `UserBase` by adding a password field and validation for student-specific fields.

    Attributes:
        password (str): The user's password. Must be at least 8 characters long.
    """

    password: str = Field(
        ..., min_length=8, description="User password (minimum 8 characters)"
    )

    @field_validator("registration_number", "cpf")
    @classmethod
    def validate_student_fields(cls, value: Optional[str], info: ValidationInfo):
        """
        Validates that 'registration_number' and 'cpf' are provided if the user_type is STUDENT,
        and not provided if the user_type is not STUDENT.
        """
        is_student = info.data.get("user_type") == UserType.STUDENT

        if is_student and value is None:
            raise ValueError("CPF and registration number are required for students.")

        if not is_student and value is not None:
            raise ValueError(
                "CPF and registration number should not be provided for staff members."
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
    """
    Schema for updating an existing user's information.

    All fields are optional, allowing for partial updates.

    Attributes:
        email (Optional[EmailStr]): The user's email address.
        full_name (Optional[str]): The full name of the user.
        user_type (Optional[UserType]): The type of user.
        password (Optional[str]): The user's new password.
        is_active (Optional[bool]): The active status of the user account.
        registration_number (Optional[str]): The student's registration number.
        cpf (Optional[str]): The student's CPF.
    """

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
    """
    Full user schema for responses, extending `UserBase` with database-generated fields.

    Attributes:
        id (int): The unique identifier of the user.
        created_at (datetime): The timestamp when the user account was created.
        updated_at (datetime): The timestamp when the user account was last updated.
    """

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


class TeamMemberResponse(BaseModel):
    """
    Schema específico para a resposta da rota /notices/{id}/team
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    user_type: UserType
    last_review: Optional[Any] = None
    progress: int
