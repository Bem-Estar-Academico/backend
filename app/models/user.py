"""User model."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.notice import Notice


class UserType(enum.Enum):
    """Enum for user types in the BEA system."""

    COORDINATOR = "COORDINATOR"
    STUDENT = "STUDENT"
    SOCIAL_WORKER = "SOCIAL_WORKER"
    NTI = "NTI"


class User(Base):
    """User model."""

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

    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    notices: Mapped[list["Notice"]] = relationship(
        "Notice", back_populates="coordinator"
    )

    @property
    def is_coordinator(self) -> bool:
        return self.user_type == UserType.COORDINATOR

    @property
    def is_student(self) -> bool:
        return self.user_type == UserType.STUDENT

    @property
    def is_social_worker(self) -> bool:
        return self.user_type == UserType.SOCIAL_WORKER

    @property
    def is_nti(self) -> bool:
        return self.user_type == UserType.NTI

    @property
    def is_staff(self) -> bool:
        return self.user_type in [
            UserType.COORDINATOR,
            UserType.SOCIAL_WORKER,
            UserType.NTI,
        ]

    def to_dict(self) -> dict:
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "user_type": self.user_type.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
