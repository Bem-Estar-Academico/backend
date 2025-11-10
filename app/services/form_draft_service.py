from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_draft import FormDraft, FormSketchType
from app.schemas.form_draft import FormDraftUpdate
from app.services.review_registration_service import ReviewRegistrationService


class FormDraftService:
    @staticmethod
    async def create_form_draft(
        db: AsyncSession,
        notice_id: int,
        user_id: int,
        draft_type: FormSketchType,
        content: Optional[Dict[str, Any]] = None,
    ) -> FormDraft:
        """
        Creates a new form draft in the database.
        """
        new_draft = FormDraft(
            notice_id=notice_id,
            user_id=user_id,
            type=draft_type,
            content=content,
        )
        db.add(new_draft)
        await db.commit()
        await db.refresh(new_draft)
        return new_draft

    @staticmethod
    async def get_form_draft(
        db: AsyncSession,
        notice_id: int,
        user_id: int,
        draft_type: FormSketchType,
    ) -> Optional[FormDraft]:
        """
        Retrieves a form draft from the database.
        """
        result = await db.execute(
            select(FormDraft).where(
                FormDraft.notice_id == notice_id,
                FormDraft.user_id == user_id,
                FormDraft.type == draft_type,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_form_draft_by_review(
        db: AsyncSession,
        review_id: int,
    ) -> Optional[FormDraft]:
        """
        Retrieves a form draft for a specific review from the database.
        """
        review = await ReviewRegistrationService.get_review_by_id(db, review_id)
        if not review:
            return None

        notice_id = review.student_registration.notice_id
        user_id = review.student_registration.student_id

        result = await db.execute(
            select(FormDraft).where(
                FormDraft.notice_id == notice_id,
                FormDraft.user_id == user_id,
                FormDraft.type == FormSketchType.REVIEW,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def update_form_draft(
        db: AsyncSession,
        notice_id: int,
        user_id: int,
        draft_type: FormSketchType,
        form_data: FormDraftUpdate,
    ) -> FormDraft:
        """
        Updates an existing form draft in the database.
        If no draft exists, it creates a new one.
        """
        draft = await FormDraftService.get_form_draft(
            db, notice_id, user_id, draft_type
        )
        if draft:
            draft.content = form_data.content
            db.add(draft)
            await db.commit()
            await db.refresh(draft)
        else:
            draft = await FormDraftService.create_form_draft(
                db, notice_id, user_id, draft_type, form_data.content
            )
        return draft

    @staticmethod
    async def update_review_form_draft(
        db: AsyncSession,
        review_id: int,
        form_data: FormDraftUpdate,
    ) -> FormDraft:
        """
        Updates an existing form draft for a review in the database.
        If no draft exists, it creates a new one.
        """
        review = await ReviewRegistrationService.get_review_by_id(db, review_id)
        if not review:
            raise ValueError("Review not found")

        notice_id = review.student_registration.notice_id
        user_id = review.student_registration.student_id

        return await FormDraftService.update_form_draft(
            db,
            notice_id=notice_id,
            user_id=user_id,
            draft_type=FormSketchType.REVIEW,
            form_data=form_data,
        )
