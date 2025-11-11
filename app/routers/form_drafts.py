from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.form_draft import FormSketchType
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas import form_draft as form_draft_schema
from app.services.form_draft_service import FormDraftService

router = APIRouter(prefix="/form-drafts", tags=["form_draft"])


@router.get(
    "/reviews/{review_id}",
    summary="Get form draft for a specific review",
    response_model=form_draft_schema.FormDraft,
)
async def get_review_form_draft(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await FormDraftService.get_form_draft_by_review(
        db,
        review_id=review_id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form draft not found for this review.",
        )
    return result


@router.get(
    "/registrations/{notice_id}",
    summary="Get form draft for a specific registration",
    response_model=form_draft_schema.FormDraft,
)
async def get_registration_form_draft(
    notice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await FormDraftService.get_form_draft(
        db,
        notice_id=notice_id,
        user_id=current_user.id,
        draft_type=FormSketchType.REGISTRATION,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form draft not found for this registration.",
        )

    if not current_user.is_staff and result.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form draft not found for this registration.",
        )

    return result


@router.put(
    "/registrations/{notice_id}",
    summary="Update form draft for a specific registration",
    response_model=form_draft_schema.FormDraft,
)
async def update_registration_form_draft(
    notice_id: int,
    form_data: form_draft_schema.FormDraftUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await FormDraftService.update_form_draft(
        db,
        notice_id=notice_id,
        user_id=current_user.id,
        draft_type=FormSketchType.REGISTRATION,
        form_data=form_data,
    )

    return result


@router.put(
    "/reviews/{review_id}",
    summary="Update form draft for a specific review",
    response_model=form_draft_schema.FormDraft,
)
async def update_review_form_draft(
    review_id: int,
    form_data: form_draft_schema.FormDraftUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff users can update review form drafts.",
        )

    result = await FormDraftService.update_review_form_draft(
        db,
        review_id=review_id,
        form_data=form_data,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form draft not found for this review.",
        )

    return result
