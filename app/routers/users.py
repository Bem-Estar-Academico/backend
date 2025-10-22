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
    user_type: UserType = UserType.SOCIAL_WORKER,
    db: AsyncSession = Depends(get_db),
) -> List[UserSchema]:
    users = await UserService.get_users(
        db, skip=skip, limit=limit, user_type=user_type
    )
    return [UserSchema.model_validate(u, from_attributes=True) for u in users]
