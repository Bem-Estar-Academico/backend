"""Module for defining the StudentRegistration model and its status enum."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.notice import Notice
    from app.models.review import ReviewRegistrationModel


class RegistrationStatus(enum.Enum):
    """Enumeration for the possible statuses of a student's registration for a notice."""
    PENDING = "PENDING"  # Aguardando análise
    APPROVED = "APPROVED"  # Aprovada
    REJECTED = "REJECTED"  # Rejeitada
    CANCELLED = "CANCELLED"  # Cancelada pelo estudante
    APPEAL = "APPEAL"  # Em fase de recurso
    REVIEW = "REVIEW" # Em análise



class StudentRegistration(Base):
    """
    Represents a student's registration for a specific notice.

    This model tracks the status of a student's application to a notice,
    including their submitted answers and relevant timestamps.

    Attributes:
        id (int): Primary key of the student registration.
        student_id (int): Foreign key to the registering student (User).
        notice_id (int): Foreign key to the notice being registered for.
        status (RegistrationStatus): The current status of the registration (e.g., PENDING, APPROVED).
        registration_date (datetime): The date and time when the student registered.
        answer (Optional[Dict[str, Any]]): A JSON field storing the student's answers to the notice questions.
        created_at (datetime): Timestamp of when the registration was created.
        updated_at (datetime): Timestamp of the last update to the registration.
    """
    __tablename__ = "student_registrations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"), nullable=False)
    
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus), default=RegistrationStatus.PENDING, nullable=False
    )
    
    registration_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    answer: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON data containing the student's answers to the notice questions",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    student: Mapped["User"] = relationship(
        "User", 
        foreign_keys=[student_id]
    )
    notice: Mapped["Notice"] = relationship(
        "Notice", 
        back_populates="registrations"
    )
    review: Mapped["ReviewRegistrationModel"] = relationship(
        "ReviewRegistrationModel",
        back_populates="student_registration",
        cascade="all, delete-orphan",
        uselist=False,
    )