"""Service layer for appeal operations."""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.appeal import Appeal
from app.models.review import ReviewRegistrationModel
from app.models.user import User
from app.schemas.appeal import AppealCreate, AppealUpdate


class AppealService:
    """Service class for managing appeals."""

    @staticmethod
    async def create_appeal(
        db: AsyncSession,
        requested_documents_data: Dict[str, Any],
        review_registration_id: int,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Creates a new appeal for a specific review registration.

        Args:
            db: The database session.
            appeal_data: The data for the new appeal.
            review_registration_id: The ID of the review being appealed.
            current_user: The user creating the appeal.

        Returns:
            The created Appeal object.

        Raises:
            HTTPException 404: If the review registration is not found.
            HTTPException 403: If the user is not the owner of the registration.
            HTTPException 400: If an appeal already exists for this review.
        """
        
        
        review = await db.get(
            ReviewRegistrationModel, 
            review_registration_id,
            options=[selectinload(ReviewRegistrationModel.student_registration)] 
        )
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review registration not found."
            )

        if review.social_worker_id != current_user.id:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only appeal your own registration reviews."
            )
            
        db_appeal = Appeal(
            requested_documents=requested_documents_data,
            review_registration_id=review_registration_id
        )
        
        db.add(db_appeal)
        await db.commit()
        await db.refresh(db_appeal)
        
        return db_appeal.requested_documents

    @staticmethod
    async def get_appeal_by_id(db: AsyncSession, appeal_id: int) -> Optional[Appeal]:
        """Retrieves an appeal by its ID."""
        
        return await db.get(
            Appeal, 
            appeal_id, 
            options=[selectinload(Appeal.review_registration)]
        )

    @staticmethod
    async def get_appeals_by_review_id(db: AsyncSession, review_registration_id: int) -> List[Appeal]:
        """Retrieves an appeal linked to a specific review registration ID."""
        
        result = await db.execute(
            select(Appeal)
            .options(selectinload(Appeal.review_registration))
            .where(Appeal.review_registration_id == review_registration_id)
        )
        
        appeal_objs_list = list(result.scalars().all())
        return [appeal.requested_documents for appeal in appeal_objs_list]

    @staticmethod
    async def update_appeal(
        db: AsyncSession,
        appeal_id: int,
        appeal_data: AppealUpdate,
        current_user: User
    ) -> Optional[Appeal]:
        """
        Updates an existing appeal. Primarily for staff/coordinators maybe?
        Or maybe students can update it before review? Define permission logic.
        """
        db_appeal = await AppealService.get_appeal_by_id(db, appeal_id)
        if not db_appeal:
            return None

        if not current_user.is_staff:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

        update_data = appeal_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_appeal, key, value)

        await db.commit()
        await db.refresh(db_appeal)
        return db_appeal

    @staticmethod
    async def delete_appeal(db: AsyncSession, appeal_id: int, current_user: User) -> bool:
        """
        Deletes an appeal. Permissions needed (e.g., only coordinator?).
        """
        db_appeal = await AppealService.get_appeal_by_id(db, appeal_id)
        if not db_appeal:
            return False

        await db.delete(db_appeal)
        await db.commit()
        return True