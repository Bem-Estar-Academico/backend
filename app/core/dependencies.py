"""Shared API dependencies."""

from fastapi import Depends, HTTPException, status

from app.models.user import User, UserType
from app.routers.auth import get_current_user


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
            detail="Only coordinators can perform this action",
        )
    return current_user

async def require_social_worker(current_user: User = Depends(get_current_user)) -> User:
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
    if current_user.user_type != UserType.SOCIAL_WORKER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only social workers can perform this action",
        )
    return current_user

async def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that checks if the current user is a staff.

    This function is used to protect endpoints that should only be accessible
    by users with the `STAFF` role.

    Args:
        current_user (User): The authenticated user object.

    Raises:
        HTTPException: If the current user is not a staff, with a 403 Forbidden status.

    Returns:
        User: The current user object if they are a staff.
    """
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can perform this action",
        )
    return current_user
