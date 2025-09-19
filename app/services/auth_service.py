"""
Authentication service layer for user authentication and token management.
"""

from datetime import timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.models.user import User
from app.services.user_service import UserService


class AuthService:
    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        return await UserService.authenticate_user(db, email, password)

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            subject=user.email, expires_delta=access_token_expires
        )

    @staticmethod
    async def get_current_user_from_token(
        db: AsyncSession, token: str
    ) -> Optional[User]:
        try:
            payload = decode_access_token(token)
            email: str = payload.get("sub")
            if email is None:
                return None
        except (ValueError, Exception):
            return None

        return await UserService.get_user_by_email(db, email)

    @staticmethod
    def validate_token(token: str) -> bool:
        try:
            payload = decode_access_token(token)
            return payload.get("sub") is not None
        except (ValueError, Exception):
            return False

    @staticmethod
    async def register_user(db: AsyncSession, user_data) -> User:
        return await UserService.create_user(db, user_data)
