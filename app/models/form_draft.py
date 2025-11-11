import enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.notice import Notice
    from app.models.user import User


class FormSketchType(enum.Enum):
    REVIEW = "REVIEW"
    REGISTRATION = "REGISTRATION"


class FormDraft(Base):
    __tablename__ = "form_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[FormSketchType] = mapped_column(Enum(FormSketchType), nullable=False)
    content: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON data containing the student's answers to the notice questions",
    )

    notice: Mapped["Notice"] = relationship("Notice", back_populates="form_drafts")
    user: Mapped["User"] = relationship("User", back_populates="form_drafts")
