"""Router for managing notices and related operations."""

"""
This module defines the API endpoints for creating, retrieving, updating, and deleting notices.
It also includes endpoints for managing documents and team members associated with notices,
and enforces role-based access control for certain operations.
"""

from typing import List, Optional, Sequence, Union

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_coordinator
from app.db.database import get_db
from app.models.user import User, UserType
from app.schemas.notice import DocumentWithUrl
from app.schemas.notice import Notice as NoticeSchema
from app.schemas.notice import (
    NoticeCreate,
    NoticeForStudent,
    NoticeTeamMember,
    NoticeUpdate,
)
from app.schemas.user import TeamMemberResponse
from app.services.notice_service import NoticeService

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("/", response_model=Union[List[NoticeSchema], List[NoticeForStudent]])
async def list_notices(
    skip: int = 0,
    limit: int = 100,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[Sequence[NoticeSchema], List[NoticeForStudent]]:
    """
    Retrieves a list of notices.

    For students, returns notices with registration status and without team_members.
    For coordinators/admins, returns full notice data including team_members.

    Args:
        skip (int): The number of items to skip (for pagination).
        limit (int): The maximum number of items to return (for pagination).
        year (Optional[int]): Optional. Filter notices by year.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Returns:
        Union[Sequence[NoticeSchema], List[NoticeForStudent]]: A list of notice objects.
    """
    if current_user.user_type == UserType.STUDENT:
        notices_with_status = await NoticeService.get_notices_for_student(
            db, student_id=current_user.id, skip=skip, limit=limit, year=year
        )
        return [NoticeForStudent(**notice) for notice in notices_with_status]

    notices = await NoticeService.get_notices(db, skip=skip, limit=limit, year=year)
    return notices


@router.get("/active", response_model=List[NoticeSchema])
async def get_active_notices(
    db: AsyncSession = Depends(get_db),
) -> Sequence[NoticeSchema]:
    """
    Retrieves a list of currently active notices.

    Args:
        db (AsyncSession): The database session.

    Returns:
        Sequence[NoticeSchema]: A list of active notice objects.
    """
    notices = await NoticeService.get_active_notices(db)
    return notices


@router.get("/year/{year}", response_model=List[NoticeSchema])
async def get_notices_by_year(
    year: int, db: AsyncSession = Depends(get_db)
) -> Sequence[NoticeSchema]:
    """
    Retrieves a list of notices for a specific year.

    Args:
        year (int): The year to filter notices by.
        db (AsyncSession): The database session.

    Returns:
        Sequence[NoticeSchema]: A list of notice objects for the specified year.
    """
    notices = await NoticeService.get_notices_by_year(db, year)
    return notices


@router.get("/{notice_id}", response_model=NoticeSchema)
async def get_notice(
    notice_id: int, db: AsyncSession = Depends(get_db)
) -> NoticeSchema:
    """
    Retrieves a single notice by its ID.

    Args:
        notice_id (int): The ID of the notice to retrieve.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the notice with the given ID is not found.

    Returns:
        NoticeSchema: The notice object.
    """
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
) -> NoticeSchema:
    """
    Creates a new notice.

    This endpoint is restricted to coordinator users.

    Args:
        notice_data (NoticeCreate): The data for creating the new notice.
        current_user (User): The authenticated coordinator user.
        db (AsyncSession): The database session.

    Returns:
        NoticeSchema: The newly created notice object.
    """
    notice = await NoticeService.create_notice(db, notice_data, current_user.id)
    return notice


@router.put("/{notice_id}", response_model=NoticeSchema)
async def update_notice(
    notice_id: int,
    notice_update: NoticeUpdate,
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
) -> NoticeSchema:
    """
    Updates an existing notice.

    This endpoint is restricted to coordinator users who are part of the notice's team.

    Args:
        notice_id (int): The ID of the notice to update.
        notice_update (NoticeUpdate): The updated data for the notice.
        current_user (User): The authenticated coordinator user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the notice is not found or the user is not authorized.

    Returns:
        NoticeSchema: The updated notice object.
    """
    existing_notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not existing_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
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
) -> None:
    """
    Deletes a notice by its ID.

    This endpoint is restricted to coordinator users who are part of the notice's team.

    Args:
        notice_id (int): The ID of the notice to delete.
        current_user (User): The authenticated coordinator user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the notice is not found or the user is not authorized.

    Returns:
        None
    """
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
) -> NoticeTeamMember:
    """
    Adds a team member (coordinator or social worker) to a specific notice.

    This endpoint is restricted to coordinator users.

    Args:
        notice_id (int): The ID of the notice to add the team member to.
        user_id (int): The ID of the user to add as a team member.
        current_user (User): The authenticated coordinator user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the notice is not found, the role is invalid, or the user is already in the team.

    Returns:
        NoticeTeamMember: The newly added notice team member object.
    """

    existing_notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not existing_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    team_member = await NoticeService.add_team_member_to_notice(db, notice_id, user_id)
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
) -> DocumentWithUrl:
    """
    Uploads a document and associates it with a specific notice.

    This endpoint is restricted to coordinator users.

    Args:
        notice_id (int): The ID of the notice to associate the document with.
        file (UploadFile): The document file to upload.
        current_user (User): The authenticated coordinator user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the notice is not found, filename is missing, file size exceeds limit, or upload fails.

    Returns:
        DocumentWithUrl: The uploaded document's information, including a presigned URL for download.
    """
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


@router.get("/{notice_id}/team", response_model=List[TeamMemberResponse])
async def get_team_to_notice(
    notice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
) -> List[TeamMemberResponse]:
    """
    Retrieves the list of team members (coordinators and social workers)
    associated with a specific notice.

    Args:
        notice_id (int): The ID of the notice.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the notice with the given ID is not found.

    Returns:
        List[TeamMemberResponse]: A list of team member objects.
    """

    existing_notice = await NoticeService.get_notice_by_id(db, notice_id)
    if not existing_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    team_members = await NoticeService.get_team_for_notice(db, notice_id=notice_id)

    return team_members
