from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.user import User as UserSchema
from app.schemas.user import UserType

router = APIRouter(prefix="/users", tags=["users"])


async def require_coordinator(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be a coordinator."""
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
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = (
        select(User)
        .offset(skip)
        .limit(limit)
        .where(User.user_type == UserType.SOCIAL_WORKER)
    )

    result = await db.execute(query)
    users = result.scalars().all()
    return users
