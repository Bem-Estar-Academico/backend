import enum
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.audit import AuditLog
    from app.models.form_draft import FormDraft
    from app.models.review import ReviewRegistrationModel


"""Module for defining the User model and related enumerations."""

"""
This module defines the `User` SQLAlchemy model, representing users in the system,
and the `UserType` enumeration, which categorizes different types of users.
It includes fields for user authentication, personal information, and role-based
properties.
"""
"""Module for defining the User model and related enumerations."""

"""
This module defines the `User` SQLAlchemy model, representing users in the system,
and the `UserType` enumeration, which categorizes different types of users.
It includes fields for user authentication, personal information, and role-based
properties.
"""


class UserType(enum.Enum):
    """Enum for user types in the BEA system."""

    NTI = "NTI"
    STUDENT = "STUDENT"
    COORDINATOR = "COORDINATOR"
    SOCIAL_WORKER = "SOCIAL_WORKER"


class User(Base):
    """
    Represents a user in the system.

    This model stores user-related information, including authentication credentials,
    personal details, and role-based attributes. It supports different user types
    defined by the `UserType` enum.

    Attributes:
        id (int): Primary key of the user.
        email (str): Unique email address of the user.
        full_name (str): Full name of the user.
        user_type (UserType): The type of user (e.g., STUDENT, COORDINATOR).
        registration_number (Optional[str]): Student registration number, if applicable.
        cpf (Optional[str]): CPF of the student, if applicable.
        hashed_password (str): Hashed password for user authentication.
        is_active (bool): Indicates if the user account is active.
        created_at (datetime): Timestamp of when the user account was created.
        updated_at (datetime): Timestamp of the last update to the user account.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType),
        nullable=False,
        comment="Type of user: coordinator, student, social_worker, or nti",
    )
    registration_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
        index=True,
        comment="Número de matrícula do estudante (apenas para user_type=STUDENT)",
    )
    cpf: Mapped[Optional[str]] = mapped_column(
        String(14),
        nullable=True,
        unique=True,
        index=True,
        comment="CPF do estudante (apenas para user_type=STUDENT)",
    )

    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=now(),
        onupdate=now(),
        nullable=False,
    )

    reviews: Mapped[List["ReviewRegistrationModel"]] = relationship(
        "ReviewRegistrationModel", back_populates="social_worker"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    form_drafts: Mapped[List["FormDraft"]] = relationship(
        "FormDraft", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_coordinator(self) -> bool:
        """Checks if the user is a coordinator."""
        return self.user_type == UserType.COORDINATOR

    @property
    def is_student(self) -> bool:
        """Checks if the user is a student."""
        return self.user_type == UserType.STUDENT

    @property
    def is_social_worker(self) -> bool:
        """Checks if the user is a social worker."""
        return self.user_type == UserType.SOCIAL_WORKER

    @property
    def is_nti(self) -> bool:
        """Checks if the user is an NTI member."""
        return self.user_type == UserType.NTI

    @property
    def is_staff(self) -> bool:
        """Checks if the user is a staff member (coordinator, social worker, or NTI)."""
        return self.user_type in [
            UserType.COORDINATOR,
            UserType.SOCIAL_WORKER,
            UserType.NTI,
        ]

    def to_dict(self) -> Dict[str, object]:
        """
        Converts the User object to a dictionary representation.

        Returns:
            Dict[str, object]: A dictionary containing the user's id, email, full name,
                               user type, active status, creation and update timestamps.
                               If the user is a student, it also includes registration number and CPF.
        """
        data: Dict[str, object] = {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "user_type": self.user_type.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        if self.is_student:
            data.update(
                {
                    "registration_number": self.registration_number,
                    "cpf": self.cpf,
                }
            )

        return data
