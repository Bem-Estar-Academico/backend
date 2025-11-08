from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_coordinator
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import User as UserSchema
from app.schemas.user import UserType
from app.services.user_service import UserService

"""Router for user-related operations."""

"""
This module defines the API endpoints for managing users, including listing users
and enforcing role-based access control.
"""

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserSchema])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_coordinator),
    user_type: UserType = UserType.SOCIAL_WORKER,
    db: AsyncSession = Depends(get_db),
) -> List[UserSchema]:
    """
    Retrieves a list of users, with optional filtering by user type.

    This endpoint is restricted to coordinator users.

    Args:
        skip (int): The number of items to skip (for pagination).
        limit (int): The maximum number of items to return (for pagination).
        current_user (User): The authenticated coordinator user.
        user_type (UserType): Optional. Filter users by their type (e.g., SOCIAL_WORKER).
        db (AsyncSession): The database session.

    Returns:
        List[UserSchema]: A list of user objects.
    """
    users = await UserService.get_users(db, skip=skip, limit=limit, user_type=user_type)
    return [UserSchema.model_validate(u, from_attributes=True) for u in users]
