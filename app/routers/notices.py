from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User, UserType
from app.routers.auth import get_current_user
from app.schemas.notice import Notice as NoticeSchema
from app.schemas.notice import NoticeBase, NoticeCreate, NoticeUpdate
from app.services.notice_service import NoticeService

router = APIRouter(prefix="/notices", tags=["notices"])


async def require_coordinator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.user_type != UserType.COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators can perform this action",
        )
    return current_user


@router.get("/", response_model=List[NoticeSchema])
async def list_notices(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> Any:
    notices = await NoticeService.get_notices(db, skip=skip, limit=limit)
    return notices


@router.get("/active", response_model=List[NoticeSchema])
async def get_active_notices(db: AsyncSession = Depends(get_db)) -> Any:
    notices = await NoticeService.get_active_notices(db)
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
    notice_data: NoticeBase,
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
) -> Any:
    notice_data = NoticeCreate(
        **notice_data.model_dump(), coordinator_id=current_user.id
    )

    notice = await NoticeService.create_notice(db, notice_data)
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

    if existing_notice.coordinator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own notices",
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

    if existing_notice.coordinator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own notices",
        )

    success = await NoticeService.delete_notice(db, notice_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    return
