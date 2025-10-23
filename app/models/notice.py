"""Module for defining notice-related models."""

"""
This module defines several SQLAlchemy models related to notices, including:
- `RegistrationStatus`: An enumeration for the status of student registrations.
- `Document`: Represents documents associated with a notice.
- `NoticeTeam`: Represents team members assigned to a specific notice.
- `Notice`: The main model for notices, containing details about various allowances and dates.
- `StudentRegistration`: Represents a student's registration for a notice.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class RegistrationStatus(enum.Enum):
    """Enumeration for the possible statuses of a student's registration for a notice."""
    PENDING = "PENDING"  # Aguardando análise
    APPROVED = "APPROVED"  # Aprovada
    REJECTED = "REJECTED"  # Rejeitada
    CANCELLED = "CANCELLED"  # Cancelada pelo estudante
    APPEAL = "APPEAL"  # Em fase de recurso
    REVIEW = "REVIEW" # Em análise

class Document(Base):
    """
    Represents a document associated with a notice.

    Attributes:
        id (int): Primary key of the document.
        notice_id (int): Foreign key to the associated notice.
        name (str): Name of the document.
        file_key (str): S3 key for the stored file.
        file_type (Optional[str]): Type of the file (e.g., PDF, DOC).
        file_size (Optional[int]): Size of the file in bytes.
        uploaded_at (datetime): Timestamp when the document was uploaded.
    """
    __tablename__ = "notice_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"), nullable=False)
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Nome do documento"
    )
    file_key: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="Chave do arquivo no S3"
    )
    file_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Tipo do arquivo (PDF, DOC, etc.)"
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Tamanho do arquivo em bytes"
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    notice: Mapped["Notice"] = relationship("Notice", back_populates="documents")

    @property
    def file_url(self) -> str:
        """Generate a signed URL for the document."""
        from app.core.s3_manager import s3_manager

        return s3_manager.generate_presigned_download_url(self.file_key)


class NoticeTeam(Base):
    """
    Represents a team member assigned to a specific notice.

    This model links users (coordinators or social workers) to notices,
    defining their role within the context of that notice.

    Attributes:
        id (int): Primary key of the notice team entry.
        notice_id (int): Foreign key to the associated notice.
        user_id (int): Foreign key to the assigned user.
        role (str): The role of the user in the notice (e.g., 'COORDINATOR', 'SOCIAL_WORKER').
        assigned_at (datetime): Timestamp when the user was assigned to the notice.
    """
    __tablename__ = "notice_teams"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    notice: Mapped["Notice"] = relationship("Notice", back_populates="team_members")
    user: Mapped["User"] = relationship("User")


class Notice(Base):
    """
    Represents a notice (edital) in the system.

    This model stores all details related to a public notice, including its
    timeline, available allowances, and associated documents and team members.

    Attributes:
        id (int): Primary key of the notice.
        title (str): The title of the notice.
        year (int): The year the notice is valid for.
        registration_start_date (datetime): The start date for student registrations.
        registration_end_date (Optional[datetime]): The end date for student registrations.
        appeal_start_date (Optional[datetime]): The start date for the appeal phase.
        appeal_end_date (Optional[datetime]): The end date for the appeal phase.
        preliminary_result_date (Optional[datetime]): The date for the preliminary results announcement.
        final_result_date (Optional[datetime]): The date for the final results announcement.
        description (str): A detailed description of the notice.
        food_allowance (bool): Indicates if food allowance is offered.
        housing_allowance (bool): Indicates if housing allowance is offered.
        daycare_allowance (bool): Indicates if daycare allowance is offered.
        graduation_scholarship (bool): Indicates if a graduation scholarship is offered.
        created_at (datetime): Timestamp of when the notice was created.
        updated_at (datetime): Timestamp of the last update to the notice.
    """
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    registration_start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data de início das inscrições"
    )
    registration_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de término das inscrições",
    )
    appeal_start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de início da fase de recursos",
    )
    appeal_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de término da fase de recursos",
    )
    preliminary_result_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de divulgação do resultado preliminar",
    )
    final_result_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de divulgação do resultado final",
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)

    food_allowance: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Auxílio Alimentação"
    )
    housing_allowance: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Auxílio Moradia"
    )
    daycare_allowance: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Auxílio Creche"
    )
    graduation_scholarship: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Bolsa Pró-Graduando"
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

    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="notice", cascade="all, delete-orphan"
    )
    team_members: Mapped[List["NoticeTeam"]] = relationship(
        "NoticeTeam", back_populates="notice", cascade="all, delete-orphan"
    )
    registrations: Mapped[List["StudentRegistration"]] = relationship(
        "StudentRegistration", back_populates="notice", cascade="all, delete-orphan"
    )


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
        comment="Stores student answers to notice-specific questions in JSON format",
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

    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])
    notice: Mapped["Notice"] = relationship("Notice", back_populates="registrations")
