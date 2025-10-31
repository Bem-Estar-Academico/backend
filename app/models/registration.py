"""Module for defining the StudentRegistration model and its status enum."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.notice import Notice, StudentDocument
    from app.models.review import ReviewRegistrationModel
    from app.models.user import User


class StudentRegistration(Base):
    """
    Represents a student's registration for a specific notice.

    This model tracks the status of a student's application to a notice,
    including their submitted answers, requested benefits, and relevant timestamps.

    Attributes:
        id (int): Primary key of the student registration.
        student_id (int): Foreign key to the registering student (User).
        notice_id (int): Foreign key to the notice being registered for.
        answer (Optional[Dict[str, Any]]): A JSON field storing the student's answers to the notice questions.
        requested_food_allowance (bool): Whether the student requested food allowance benefit.
        requested_housing_allowance (bool): Whether the student requested housing allowance benefit.
        requested_daycare_allowance (bool): Whether the student requested daycare allowance benefit.
        requested_graduation_scholarship (bool): Whether the student requested graduation scholarship benefit.
        created_at (datetime): Timestamp of when the registration was created.
        updated_at (datetime): Timestamp of the last update to the registration.
    """

    __tablename__ = "student_registrations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"), nullable=False)
    
    answer: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON data containing the student's answers to the notice questions",
    )

    requested_food_allowance: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    requested_housing_allowance: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    requested_daycare_allowance: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    requested_graduation_scholarship: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=now(),
        onupdate=now(),
        nullable=False,
    )
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])
    notice: Mapped["Notice"] = relationship("Notice", back_populates="registrations")
    review: Mapped[Optional["ReviewRegistrationModel"]] = relationship(
        "ReviewRegistrationModel",
        back_populates="student_registration",
        cascade="all, delete-orphan",
        uselist=False,
    )
    documents: Mapped[List["StudentDocument"]] = relationship(
        "StudentDocument",
        back_populates="student_registration",
        cascade="all, delete-orphan",
    )
