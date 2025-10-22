import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class RegistrationStatus(enum.Enum):
    PENDING = "PENDENTE"  # Aguardando análise
    APPROVED = "DEFERIDO"  # Aprovada
    REJECTED = "INDEFERIDO"  # Rejeitada
    CANCELLED = "CANCELADO"  # Cancelada pelo estudante
    APPEAL = "RECURSO"  # Em fase de recurso

class Document(Base):
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
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
