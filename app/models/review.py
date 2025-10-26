"""Module for defining the ReviewRegistration model."""

"""
This module defines the `ReviewRegistration` SQLAlchemy model, representing a
social worker's review of a student's registration. It links users (social workers)
and student registrations, storing the review details and the calculated IVS.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.registration import StudentRegistration
    from app.models.user import User


class ReviewRegistrationModel(Base):
    """
    Represents a review of a student registration in the database.

    This model stores the social worker's assessment, the calculated IVS,
    benefit approvals, and links to the associated social worker (User) and the
    StudentRegistration.

    Attributes:
        id (int): Primary key of the review.
        social_worker_id (int): Foreign key linking to the User (social worker).
        student_registration_id (int): Foreign key linking to the StudentRegistration.
                                       This is unique, enforcing a one-to-one relationship.
        review (dict): JSON blob containing the structured review data.
        ivs (float): The calculated vulnerability score (Índice de Vulnerabilidade Social).
        approved_food_allowance (Optional[bool]): Whether food allowance benefit was approved.
        approved_housing_allowance (Optional[bool]): Whether housing allowance benefit was approved.
        approved_daycare_allowance (Optional[bool]): Whether daycare allowance benefit was approved.
        approved_graduation_scholarship (Optional[bool]): Whether graduation scholarship benefit was approved.
        created_at (datetime): Timestamp of when the review was created.
        updated_at (datetime): Timestamp of the last update to the review.
        social_worker (User): Relationship to the User who performed the review.
        student_registration (StudentRegistration): Relationship to the registration being reviewed.
    """

    __tablename__ = "review_registrations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    social_worker_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="ID of the social worker (user) who submitted the review",
    )
    student_registration_id: Mapped[int] = mapped_column(
        ForeignKey("student_registrations.id"),
        nullable=False,
        unique=True,
        comment="ID of the student registration being reviewed (one-to-one)",
    )
    review: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="JSON payload containing the review form data",
    )
    ivs: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Calculated Vulnerability Score (IVS)",
    )

    approved_food_allowance: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether food allowance benefit was approved (null if not applicable)",
    )
    approved_housing_allowance: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether housing allowance benefit was approved (null if not applicable)",
    )
    approved_daycare_allowance: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether daycare allowance benefit was approved (null if not applicable)",
    )
    approved_graduation_scholarship: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether graduation scholarship benefit was approved (null if not applicable)",
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
    social_worker: Mapped["User"] = relationship(back_populates="reviews")
    student_registration: Mapped["StudentRegistration"] = relationship(
        back_populates="review"
    )

    def to_dict(self) -> Dict[str, object]:
        """
        Converts the ReviewRegistration object to a dictionary representation.

        Returns:
            Dict[str, object]: A dictionary containing the review's details.
        """
        return {
            "id": self.id,
            "social_worker_id": self.social_worker_id,
            "student_registration_id": self.student_registration_id,
            "review": self.review,
            "ivs": float(self.ivs),
            "approved_food_allowance": self.approved_food_allowance,
            "approved_housing_allowance": self.approved_housing_allowance,
            "approved_daycare_allowance": self.approved_daycare_allowance,
            "approved_graduation_scholarship": self.approved_graduation_scholarship,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
