from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User, UserType
from app.routers.auth import get_current_user
from app.schemas.notice import Notice as NoticeSchema
from app.schemas.notice import NoticeCreate, NoticeUpdate
from app.services.notice_service import NoticeService

router = APIRouter(prefix="/notices", tags=["notices"])


async def require_coordinator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.user_type != UserType.COORDINATOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators can perform this action",
        )
    return current_user


@router.get("/", response_model=List[NoticeSchema])
async def list_notices(
    skip: int = 0,
    limit: int = 100,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    notices = await NoticeService.get_notices(db, skip=skip, limit=limit, year=year)
    return notices


@router.get("/active", response_model=List[NoticeSchema])
async def get_active_notices(db: AsyncSession = Depends(get_db)) -> Any:
    notices = await NoticeService.get_active_notices(db)
    return notices


@router.get("/year/{year}", response_model=List[NoticeSchema])
async def get_notices_by_year(year: int, db: AsyncSession = Depends(get_db)) -> Any:
    notices = await NoticeService.get_notices_by_year(db, year)
    return notices


@router.get("/{notice_id}", response_model=NoticeSchema)
async def get_notice(notice_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )
    return notice


@router.post("/", response_model=NoticeSchema, status_code=status.HTTP_201_CREATED)
async def create_notice(
    notice_data: NoticeCreate,
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
) -> Any:
    notice = await NoticeService.create_notice(db, notice_data, current_user.id)
    return notice


@router.put("/{notice_id}", response_model=NoticeSchema)
async def update_notice(
    notice_id: int,
    notice_update: NoticeUpdate,
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
) -> Any:
    existing_notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not existing_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    user_in_team = any(
        member.user_id == current_user.id and member.role == UserType.COORDINATOR.value
        for member in existing_notice.team_members
    )

    if not user_in_team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update notices where you are a coordinator",
        )

    notice = await NoticeService.update_notice(db, notice_id, notice_update)
    return notice


@router.delete(
    "/{notice_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_notice(
    notice_id: int,
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
) -> Any:
    existing_notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not existing_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    user_in_team = any(
        member.user_id == current_user.id and member.role == "COORDINATOR"
        for member in existing_notice.team_members
    )

    if not user_in_team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete notices where you are a coordinator",
        )

    success = await NoticeService.delete_notice(db, notice_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    return


@router.post("/{notice_id}/documents")
async def add_document_to_notice(
    notice_id: int,
    document_data: dict,
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
) -> Any:
    existing_notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not existing_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    user_in_team = any(
        member.user_id == current_user.id and member.role == "COORDINATOR"
        for member in existing_notice.team_members
    )

    if not user_in_team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add documents to notices where you are a coordinator",
        )

    document = await NoticeService.add_document_to_notice(db, notice_id, document_data)
    return document


@router.post("/{notice_id}/team")
async def add_team_member_to_notice(
    notice_id: int,
    user_id: int,
    role: str,
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if role not in ["COORDINATOR", "SOCIAL_WORKER"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be COORDINATOR or SOCIAL_WORKER",
        )

    existing_notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not existing_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    user_in_team = any(
        member.user_id == current_user.id and member.role == "COORDINATOR"
        for member in existing_notice.team_members
    )

    if not user_in_team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add team members to notices where you are a coordinator",
        )

    team_member = await NoticeService.add_team_member_to_notice(
        db, notice_id, user_id, role
    )
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already in the team or user not found",
        )

    return team_member
