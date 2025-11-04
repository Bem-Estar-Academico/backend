"""
Authentication service layer for user authentication and token management.
"""

from datetime import timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user_service import UserService


class AuthService:
    """
    Service class responsible for all authentication and authorization operations,
    including user login, token creation, and token validation.

    It acts as a facade, utilizing `UserService` for database interactions and
    `app.core.security` for cryptographic operations.
    """
    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """
        Authenticates a user by checking their email and password against the database.

        Args:
            db (AsyncSession): The asynchronous database session.
            email (str): The user's email address.
            password (str): The user's plain text password.

        Returns:
            Optional[User]: The User object if authentication is successful, otherwise None.
        """
        return await UserService.authenticate_user(db, email, password)

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        """
        Creates a JWT access token for a given user.

        The expiration time is configured via application settings.

        Args:
            user (User): The authenticated User object.

        Returns:
            str: The encoded JWT access token string.
        """
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            subject=user.email, expires_delta=access_token_expires
        )

    @staticmethod
    async def get_current_user_from_token(
        db: AsyncSession, token: str
    ) -> Optional[User]:
        """
        Decodes a JWT token, extracts the user email (subject), and retrieves
        the corresponding User object from the database.

        Args:
            db (AsyncSession): The asynchronous database session.
            token (str): The JWT access token (usually from the Authorization header).

        Returns:
            Optional[User]: The User object if the token is valid and the user exists, otherwise None.
        """
        try:
            payload = decode_access_token(token)
            email: Optional[str] = payload.get("sub")
            if email is None:
                return None
        except (ValueError, Exception):
            return None

        return await UserService.get_user_by_email(db, email)

    @staticmethod
    def validate_token(token: str) -> bool:
        """
        Checks if a JWT token is structurally valid and not expired.

        It does not verify if the user still exists in the database.

        Args:
            token (str): The JWT access token.

        Returns:
            bool: True if the token is valid, False otherwise.
        """
        try:
            payload = decode_access_token(token)
            return payload.get("sub") is not None
        except (ValueError, Exception):
            return False

    @staticmethod
    async def register_user(db: AsyncSession, user_data: UserCreate) -> User:
        """
        Registers a new user in the system.

        Args:
            db (AsyncSession): The asynchronous database session.
            user_data (UserCreate): Pydantic schema containing the new user's data.

        Returns:
            User: The newly created User object.
        """
        return await UserService.create_user(db, user_data)
