"""
Service layer for managing student registration reviews.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import RegistrationStatus, ReviewRegistrationModel
from app.models.user import User
from app.schemas.review_registration import (
    ReviewRegistrationCreate,
    ReviewRegistrationUpdate,
)
from app.schemas.user import UserType
from app.services.student_registration_service import StudentRegistrationService


class ReviewRegistrationService:
    """
    Service class for all business logic related to registration reviews.
    """

    @staticmethod
    async def create_review(
        db: AsyncSession,
        social_worker: User,
        student_registration_id: int,
        review_data: ReviewRegistrationCreate,
    ) -> ReviewRegistrationModel:
        """
        Creates a new review for a student registration.

        Args:
            db (AsyncSession): The database session.
            review_data (ReviewRegistrationCreate): The review data.
            social_worker (User): The authenticated social worker creating the review.

        Returns:
            ReviewRegistrationModel: The created review object.

        Raises:
            HTTPException: If the user is not a social worker, the payload ID does not match,
                           the registration does not exist, or a review already exists.
        """
        if not social_worker.is_staff:
            raise HTTPException(
                status_code=403,
                detail="Only staff can create reviews.",
            )

        registration = await StudentRegistrationService.get_registration_by_id(
            db, student_registration_id
        )
        if not registration:
            raise HTTPException(
                status_code=404, detail="Student registration not found."
            )

        existing_review = (
            await ReviewRegistrationService.get_review_by_student_registration_id(
                db, student_registration_id
            )
        )
        if existing_review:
            raise HTTPException(
                status_code=400,
                detail="A review for this registration already exists.",
            )

        db_review = ReviewRegistrationModel(**review_data.model_dump(),
                                            social_worker_id=social_worker.id,
                                            student_registration_id=student_registration_id,
                                            status=RegistrationStatus.PENDING)
        db.add(db_review)
        await db.commit()
        await db.refresh(db_review)
        return db_review

    @staticmethod
    async def get_review_by_id(
        db: AsyncSession, review_id: int
    ) -> Optional[ReviewRegistrationModel]:
        """
        Retrieves a single review by its ID.

        Args:
            db (AsyncSession): The database session.
            review_id (int): The ID of the review.

        Returns:
            Optional[ReviewRegistrationModel]: The review object, or None if not found.
        """
        query = (
            select(ReviewRegistrationModel)
            .options(
                selectinload(ReviewRegistrationModel.social_worker),
                selectinload(ReviewRegistrationModel.student_registration),
            )
            .where(ReviewRegistrationModel.id == review_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_review_by_student_registration_id(
        db: AsyncSession, student_registration_id: int
    ) -> Optional[ReviewRegistrationModel]:
        """
        Retrieves a review by the student registration ID.

        Args:
            db (AsyncSession): The database session.
            student_registration_id (int): The ID of the student registration.

        Returns:
            Optional[ReviewRegistrationModel]: The review object, or None if not found.
        """
        query = (
            select(ReviewRegistrationModel)
            .options(
                selectinload(ReviewRegistrationModel.social_worker),
                selectinload(ReviewRegistrationModel.student_registration),
            )
            .where(
                ReviewRegistrationModel.student_registration_id == student_registration_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_review(
        db: AsyncSession,
        review_id: int,
        review_data: ReviewRegistrationUpdate,
        current_user: User,
    ) -> Optional[ReviewRegistrationModel]:
        """
        Updates an existing review.

        Args:
            db (AsyncSession): The database session.
            review_id (int): The ID of the review to update.
            review_data (ReviewRegistrationUpdate): The data to update.
            current_user (User): The user performing the update.

        Returns:
            Optional[ReviewRegistrationModel]: The updated review object, or None if not found.

        Raises:
            HTTPException: If the user does not have permission.
        """
        review = await ReviewRegistrationService.get_review_by_id(db, review_id)
        if not review:
            return None

        is_owner = review.social_worker_id == current_user.id
        is_coordinator = current_user.user_type == UserType.COORDINATOR

        if not is_owner and not is_coordinator:
            raise HTTPException(
                status_code=403, detail="Not enough permissions to update this review."
            )

        update_data = review_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(review, field, value)

        review.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(review)
        return review

    @staticmethod
    async def delete_review(db: AsyncSession, review_id: int, current_user: User) -> bool:
        """
        Deletes a review.

        Args:
            db (AsyncSession): The database session.
            review_id (int): The ID of the review to delete.
            current_user (User): The user performing the deletion.

        Returns:
            bool: True if deleted, False if not found.

        Raises:
            HTTPException: If the user does not have permission.
        """
        review = await ReviewRegistrationService.get_review_by_id(db, review_id)
        if not review:
            return False

        if current_user.user_type != UserType.COORDINATOR:
            raise HTTPException(
                status_code=403, detail="Only coordinators can delete reviews."
            )

        await db.delete(review)
        await db.commit()
        return True
