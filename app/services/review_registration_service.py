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
from app.services.appeal_service import AppealService
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
        review_data: ReviewRegistrationUpdate,  # Objeto Pydantic vindo da rota
        current_user: User,
    ) -> Optional[ReviewRegistrationModel]:
        """
        Updates an existing review and handles appeal creation/update if status is APPEAL.
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
        appeal_data = update_data.pop('appeal', None)
        calculated_ivs: Optional[float] = None
        new_status = review_data.status

        if new_status:
            if new_status in [RegistrationStatus.APPROVED, RegistrationStatus.REJECTED]:
                if not appeal_data:
                    calculated_ivs = review_data.calculete_ivs()
                    update_data.pop('ivs', None)
                else:
                   raise HTTPException(
                        status_code=400,
                        detail="The 'appeals' field is required when setting status to APPEAL."
                    ) 

            elif new_status == RegistrationStatus.APPEAL:
                if not appeal_data:
                    raise HTTPException(
                        status_code=400,
                        detail="The 'appeals' field is required when setting status to APPEAL."
                    )
                else:
                    try:
                        created_appeal = await AppealService.create_appeal(
                            db=db,
                            requested_documents_data=appeal_data,
                            review_registration_id=review_id,
                            current_user=current_user
                        )
                        if not created_appeal:
                            raise HTTPException(
                                status_code=500, detail="Failed to save appeal data.")
                    except HTTPException as http_exc:
                        raise http_exc
                    except Exception as e:
                        print(
                            f"Erro inesperado ao criar apelo para review {review_id}: {e}")
                        raise HTTPException(
                            status_code=500, detail=f"Internal error saving appeal: {e}")

        for field, value in update_data.items():
            setattr(review, field, value)

        if calculated_ivs is not None:
            review.ivs = calculated_ivs

        review.updated_at = datetime.now(timezone.utc)

        try:
            await db.commit()
            await db.refresh(review)
            return review
        except Exception as e:
            await db.rollback()
            print(f"Erro durante o commit ao atualizar review {review_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database commit error: {e}")

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
