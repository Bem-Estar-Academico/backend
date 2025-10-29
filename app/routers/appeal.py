"""API Endpoints for managing appeal."""

from typing import Any, Dict, List # Se precisar listar apelos no futuro

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user # Ou seu método de autenticação
from app.schemas.appeal import AppealCreate, AppealResponse, AppealUpdate
from app.services.appeal import AppealService
from app.services.review_registration_service import ReviewRegistrationService # Para verificar permissões

router = APIRouter(tags=["appeal"])

@router.post(
    "/reviews/{review_registration_id}/appeal", 
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Submit an appeal for a review",
)
async def create_appeal(
    review_registration_id: int,
    appeal_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a new appeal against a specific review registration decision.
    Only the student who owns the registration can create an appeal.
    """
    
    appeal = await AppealService.create_appeal(
        db, appeal_data, review_registration_id, current_user
    )
    
    return appeal

@router.get(
    "/reviews/{review_registration_id}/appeals",
    response_model=List[Dict[str, Any]],
    summary="Get the appeal for a specific review",
)
async def get_appeals_for_review(
    review_registration_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the appeal associated with a specific review registration ID.
    Accessible by the student owner or staff.
    """
    appeals = await AppealService.get_appeals_by_review_id(db, review_registration_id)
    
    if not appeals:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appeal not found for this review.")

    review = await ReviewRegistrationService.get_review_by_id(
        db, review_registration_id
    )

    if not review:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated review not found.")
         
    if review.social_worker_id != current_user.id and not current_user.is_staff:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    return appeals

@router.get(
    "/appeal/{appeal_id}",
    response_model=AppealResponse,
    summary="Get an appeal by its ID",
)
async def get_appeal(
    appeal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a specific appeal by its unique ID.
    Accessible by the student owner or staff.
    """
    appeal = await AppealService.get_appeal_by_id(db, appeal_id)
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appeal not found.")

    review = await ReviewRegistrationService.get_review_by_id(db, appeal.review_registration_id)
    if not review:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated review not found.")
         
    if review.social_worker_id != current_user.id and not current_user.is_staff:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    return appeal

@router.put(
    "/appeal/{appeal_id}",
    response_model=AppealResponse,
    summary="Update an appeal",
)
async def update_appeal(
    appeal_id: int,
    appeal_data: AppealUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates an existing appeal.
    (Permission logic needs to be defined based on business rules, e.g., only staff).
    """
    
    updated_appeal = await AppealService.update_appeal(db, appeal_id, appeal_data, current_user)
    if not updated_appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appeal not found.")
    return updated_appeal

@router.delete(
    "/appeal/{appeal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an appeal",
)
async def delete_appeal(
    appeal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes an appeal by its ID.
    (Permission logic needs to be defined, e.g., only coordinators).
    """
    deleted = await AppealService.delete_appeal(db, appeal_id, current_user)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appeal not found.")
    return None