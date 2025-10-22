"""Router for user-related operations."""

"""
This module defines the API endpoints for managing users, including listing users
and enforcing role-based access control.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.user import User as UserSchema
from app.schemas.user import UserType
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


async def require_coordinator(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that checks if the current user is a coordinator.

    This function is used to protect endpoints that should only be accessible
    by users with the `COORDINATOR` role.

    Args:
        current_user (User): The authenticated user object.

    Raises:
        HTTPException: If the current user is not a coordinator, with a 403 Forbidden status.

    Returns:
        User: The current user object if they are a coordinator.
    """
    if current_user.user_type != UserType.COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators can access this resource",
        )
    return current_user


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
    users = await UserService.get_users(
        db, skip=skip, limit=limit, user_type=user_type
    )
    return [UserSchema.model_validate(u, from_attributes=True) for u in users]
