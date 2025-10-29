"""Model for representing appeal records."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.review import ReviewRegistrationModel


class Appeal(Base):
    """
    Represents an appeal submitted against a review decision.

    An appeal is linked to a specific review registration and contains details
    about requested document resubmissions or clarifications.

    Attributes:
        id (int): Primary key.
        review_registration_id (int): Foreign key to the review being appealed.
        requested_documents (Dict[str, Any]): JSON field detailing required actions/documents.
        created_at (datetime): Timestamp of creation.
        updated_at (datetime): Timestamp of last update.
        review_registration (ReviewRegistrationModel): Relationship to the parent review.
    """
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    review_registration_id: Mapped[int] = mapped_column(
        ForeignKey("review_registrations.id"),
        nullable=False,
        unique=False,
        index=True,
        comment="ID of the review registration being appealed (one-to-one)",
    )
    
    requested_documents: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="JSON detailing requested documents and reasons for appeal",
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

    review_registration: Mapped["ReviewRegistrationModel"] = relationship(
        back_populates="appeal"
    )