from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User, UserType
from app.routers.auth import get_current_user
from app.schemas.notice import DocumentWithUrl
from app.schemas.notice import Notice as NoticeSchema
from app.schemas.notice import NoticeCreate, NoticeTeamMember, NoticeUpdate
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
    try:
        notice = await NoticeService.create_notice(db, notice_data, current_user.id)
        return notice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


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
        member.user_id == current_user.id and member. == UserType.COORDINATOR.value
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

    success = await NoticeService.delete_notice(db, notice_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    return


@router.post("/{notice_id}/team/{user_id}", response_model=NoticeTeamMember)
async def add_team_member_to_notice(
    notice_id: int,
    user_id: int,
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
) -> Any:

    existing_notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not existing_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    team_member = await NoticeService.add_team_member_to_notice(
        db, notice_id, user_id
    )
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already in the team or user not found",
        )

    return team_member


@router.post("/{notice_id}/documents", response_model=DocumentWithUrl)
async def upload_document_to_notice(
    notice_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
) -> Any:
    existing_notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not existing_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required"
        )

    max_size = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit",
        )

    try:
        document = await NoticeService.upload_document_to_notice(
            db,
            notice_id,
            file_content,
            file.filename,
            file.content_type or "application/octet-stream",
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload document",
            )

        return document

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}",
        )
