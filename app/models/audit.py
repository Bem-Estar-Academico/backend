"""
Model for audit log entries to track system actions and changes.
"""

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditAction(enum.Enum):
    """Enum for audit actions."""

    NOTICE_CREATED = "NOTICE_CREATED"
    NOTICE_UPDATED = "NOTICE_UPDATED"
    NOTICE_DELETED = "NOTICE_DELETED"
    REGISTRATION_SUBMITTED = "REGISTRATION_SUBMITTED"
    REVIEW_STARTED = "REVIEW_STARTED"
    REVIEW_UPDATED = "REVIEW_UPDATED"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    REVIEW_REJECTED = "REVIEW_REJECTED"
    APPEAL_SUBMITTED = "APPEAL_SUBMITTED"
    APPEAL_REVIEWED = "APPEAL_REVIEWED"
    SOCIAL_WORKER_ANALYSIS = "SOCIAL_WORKER_ANALYSIS"
    TEAM_MEMBER_ASSIGNED = "TEAM_MEMBER_ASSIGNED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_DELETED = "DOCUMENT_DELETED"
    STATUS_CHANGED = "STATUS_CHANGED"


class AuditEntityType(enum.Enum):
    """Enum for audit entity types."""

    NOTICE = "NOTICE"
    REVIEW = "REVIEW"
    REGISTRATION = "REGISTRATION"
    USER = "USER"
    DOCUMENT = "DOCUMENT"
    TEAM_MEMBER = "TEAM_MEMBER"
    SYSTEM = "SYSTEM"


class AuditLog(Base):
    """
    Model for audit log entries.

    Tracks all significant actions performed in the system for compliance
    and monitoring purposes.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action: Mapped[AuditAction] = mapped_column(
        String(50), nullable=False, index=True, comment="The action that was performed"
    )
    entity_type: Mapped[AuditEntityType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="The type of entity that was affected",
    )
    entity_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="The ID of the entity that was affected",
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="The user who performed the action",
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Human-readable description of the action"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address of the user who performed the action",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="User agent string of the client"
    )
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, comment="Additional context data as JSON"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="When the action was performed",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="audit_logs", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, entity_type={self.entity_type})>"
