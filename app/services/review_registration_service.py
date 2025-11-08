"""
Service layer for managing student registration reviews.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging_config import get_logger
from app.models.review import RegistrationStatus, ReviewRegistrationModel
from app.models.user import User
from app.schemas.email_notification import EmailNotificationData
from app.schemas.review_registration import (
    ReviewRegistrationCreate,
    ReviewRegistrationUpdate,
)
from app.schemas.user import UserType
from app.services.appeal_service import AppealService
from app.services.email_service import email_service
from app.services.student_registration_service import StudentRegistrationService

logger = get_logger(__name__)


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
        now = datetime.now(timezone.utc)
        if not (
            registration.notice.registration_start_date
            and registration.notice.registration_end_date
            and registration.notice.registration_start_date
            <= now
            <= registration.notice.registration_end_date
        ):
            raise HTTPException(
                status_code=400,
                detail="Reviews can only be created during the notice's active registration period.",
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

        db_review = ReviewRegistrationModel(
            **review_data.model_dump(),
            social_worker_id=social_worker.id,
            student_registration_id=student_registration_id,
        )
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
                selectinload(ReviewRegistrationModel.appeals),
            )
            .where(
                ReviewRegistrationModel.student_registration_id
                == student_registration_id
            )
        )
        result = await db.execute(query)

        data = result.scalar_one_or_none()
        return data

    @staticmethod
    async def update_review(
        db: AsyncSession,
        review_id: int,
        review_data: ReviewRegistrationUpdate,
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
        appeal_data = update_data.pop("appeal", None)
        calculated_ivs: Optional[float] = None
        new_status = review_data.status

        if new_status:
            if new_status in [RegistrationStatus.APPROVED, RegistrationStatus.REJECTED]:
                if not appeal_data:
                    calculated_ivs = review_data.calculate_ivs()
                    update_data.pop("ivs", None)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="The 'appeal' field must not be provided when setting status to APPROVED or REJECTED.",
                    )

            elif new_status == RegistrationStatus.APPEAL:
                if not appeal_data:
                    raise HTTPException(
                        status_code=400,
                        detail="The 'appeal' field is required when setting status to APPEAL.",
                    )
                else:
                    try:
                        created_appeal = await AppealService.create_appeal(
                            db=db,
                            requested_documents_data=appeal_data,
                            review_registration_id=review_id,
                            current_user=current_user,
                        )
                        if not created_appeal:
                            raise HTTPException(
                                status_code=500, detail="Failed to save appeal data."
                            )
                    except HTTPException as http_exc:
                        raise http_exc
                    except Exception as e:
                        logger.error(
                            "Erro inesperado ao criar apelo para review %s: %s",
                            review_id,
                            e,
                        )
                        raise HTTPException(
                            status_code=500, detail="Internal error saving appeal"
                        )

        for field, value in update_data.items():
            setattr(review, field, value)

        if calculated_ivs is not None:
            review.ivs = calculated_ivs

        review.updated_at = datetime.now(timezone.utc)

        try:
            await db.commit()
            await db.refresh(review)

            if new_status and new_status in [
                RegistrationStatus.APPROVED,
                RegistrationStatus.REJECTED,
                RegistrationStatus.APPEAL,
            ]:
                try:
                    await ReviewRegistrationService._send_status_email(
                        review, new_status, appeal_data
                    )
                    # Track successful notification
                    if hasattr(review, "email_notification_status"):
                        review.email_notification_status = "SENT"
                except Exception as email_exc:
                    logger.error(
                        "Failed to send status email for review %s: %s",
                        review_id,
                        email_exc,
                    )
                    # Track failed notification for retry/manual review
                    if hasattr(review, "email_notification_status"):
                        review.email_notification_status = "FAILED"
                    # Optionally, you could re-raise or just log and continue
                # Commit notification status change
                try:
                    await db.commit()
                    await db.refresh(review)
                except Exception as commit_exc:
                    logger.error(
                        "Failed to commit email notification status for review %s: %s",
                        review_id,
                        commit_exc,
                    )

            return review
        except Exception as e:
            await db.rollback()
            logger.error(
                "Erro durante o commit ao atualizar review %s: %s", review_id, e
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def delete_review(
        db: AsyncSession, review_id: int, current_user: User
    ) -> bool:
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

    @staticmethod
    def _prepare_email_notification_data(
        review: ReviewRegistrationModel,
        status: RegistrationStatus,
        appeal_data: Optional[dict] = None,
    ) -> EmailNotificationData:
        """
        Prepare email notification data from review model and appeal data.

        Args:
            review: The review registration model
            status: New status of the registration
            appeal_data: Appeal data if status is APPEAL

        Returns:
            EmailNotificationData: Structured data for email notification
        """
        student = review.student_registration.student
        notice = review.student_registration.notice

        requested_documents = None
        if status == RegistrationStatus.APPEAL and appeal_data:
            requested_documents = []

            if "requested_documents" in appeal_data:
                for doc_key, doc_value in appeal_data["requested_documents"].items():
                    if isinstance(doc_value, str):
                        requested_documents.append(f"{doc_key}: {doc_value}")

                    else:
                        requested_documents.append(doc_key)

        return EmailNotificationData(
            student_email=student.email,
            student_name=student.full_name,
            notice_title=notice.title,
            status=status,
            ivs_score=review.ivs if status == RegistrationStatus.APPROVED else None,
            requested_documents=requested_documents,
        )

    @staticmethod
    async def _send_status_email(
        review: ReviewRegistrationModel,
        status: RegistrationStatus,
        appeal_data: Optional[dict] = None,
    ):
        """
        Send email notification to student about registration status update.

        Args:
            review: The review registration model
            status: New status of the registration
            appeal_data: Appeal data if status is APPEAL
        """
        try:
            email_data = ReviewRegistrationService._prepare_email_notification_data(
                review, status, appeal_data
            )

            email_result = await email_service.send_registration_status_email(
                student_email=email_data.student_email,
                student_name=email_data.student_name,
                notice_title=email_data.notice_title,
                status=email_data.status,
                ivs_score=email_data.ivs_score,
                requested_documents=email_data.requested_documents,
            )

            if email_result.success:
                logger.info(
                    f"Status email sent to {email_data.student_email} for review {review.id}"
                )

            else:
                logger.warning(
                    f"Failed to send status email to {email_data.student_email} for review {review.id}: {email_result.message}"
                )

        except Exception as e:
            logger.error(f"Error sending status email for review {review.id}: {str(e)}")
