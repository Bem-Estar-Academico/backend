"""
User service layer for business logic and database operations.
"""

from datetime import datetime, timezone
import random
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserType, UserUpdate


class UserService:
    """
    Service class responsible for managing user accounts, including CRUD operations,
    password hashing, and authentication logic.
    """

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """
        Retrieves a single user by their unique ID.

        Args:
            db (AsyncSession): The asynchronous database session.
            user_id (int): The ID of the user to retrieve.

        Returns:
            Optional[User]: The User object, or None if not found.
        """
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """
        Retrieves a single user by their email address.

        Args:
            db (AsyncSession): The asynchronous database session.
            email (str): The email of the user to retrieve.

        Returns:
            Optional[User]: The User object, or None if not found.
        """
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_users(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_type: Optional[UserType] = None,
    ) -> List[User]:
        """
        Retrieves a list of users with pagination and optional filtering by user type.

        Args:
            db (AsyncSession): The asynchronous database session.
            skip (int): The number of records to skip (for pagination).
            limit (int): The maximum number of records to return.
            user_type (Optional[UserType]): Optional filter by user type (e.g., STUDENT, COORDINATOR).

        Returns:
            List[User]: A list of User objects.
        """
        query = select(User).offset(skip).limit(limit)

        if user_type:
            query = query.where(User.user_type == user_type)

        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_random_social_worker(db: AsyncSession) -> Optional[User]:
        """
        Fetches all social workers and returns one at random.
        
        This function may change in the future to use a different selection algorithm.
        """
        
        social_workers = await UserService.get_users(
            db, user_type=UserType.SOCIAL_WORKER, limit=1000
        )
        
        if social_workers:
            return random.choice(social_workers)

        return None
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """
        Creates a new user, performing validation checks for email, registration number, and CPF uniqueness.
        Hashes the password before storing it.

        Args:
            db (AsyncSession): The asynchronous database session.
            user_data (UserCreate): Pydantic schema with the new user's data.

        Returns:
            User: The newly created User object.

        Raises:
            ValueError: If the email, registration number (for students), or CPF (for students) is already registered.
        """
        existing_user = await UserService.get_user_by_email(db, user_data.email)

        if existing_user:
            raise ValueError("Email already registered")

        if user_data.user_type == UserType.STUDENT:
            if user_data.registration_number:
                existing_registration = await db.execute(
                    select(User).where(
                        User.registration_number == user_data.registration_number
                    )
                )
                if existing_registration.scalar_one_or_none():
                    raise ValueError("Student registration already exists")

            if user_data.cpf:
                existing_cpf = await db.execute(
                    select(User).where(User.cpf == user_data.cpf)
                )
                if existing_cpf.scalar_one_or_none():
                    raise ValueError("CPF already registered")

        hashed_password = get_password_hash(user_data.password)

        db_user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            user_type=user_data.user_type,
            hashed_password=hashed_password,
            registration_number=(
                user_data.registration_number
                if user_data.user_type == UserType.STUDENT
                else None
            ),
            cpf=user_data.cpf if user_data.user_type == UserType.STUDENT else None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        return db_user

    @staticmethod
    async def update_user(
        db: AsyncSession, user_id: int, user_update: UserUpdate
    ) -> Optional[User]:
        """
        Updates an existing user's data. Automatically hashes a new password if provided.

        Args:
            db (AsyncSession): The asynchronous database session.
            user_id (int): The ID of the user to update.
            user_update (UserUpdate): Pydantic schema with the fields to update (only non-None fields are used).

        Returns:
            Optional[User]: The updated User object, or None if the user was not found.
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None

        update_data = user_update.model_dump(exclude_unset=True)

        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )

        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> bool:
        """
        Deletes a user record by its ID.

        Args:
            db (AsyncSession): The asynchronous database session.
            user_id (int): The ID of the user to delete.

        Returns:
            bool: True if the user was deleted, False if the user was not found.
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return False

        await db.delete(user)
        await db.commit()
        return True

    @staticmethod
    async def activate_user(db: AsyncSession, user_id: int) -> Optional[User]:
        """
        Sets the `is_active` status of a user to True.

        Args:
            db (AsyncSession): The asynchronous database session.
            user_id (int): The ID of the user to activate.

        Returns:
            Optional[User]: The activated User object, or None if the user was not found.
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None

        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """
        Authenticates a user by email and password.

        Args:
            db (AsyncSession): The asynchronous database session.
            email (str): The user's email address.
            password (str): The user's plain text password.

        Returns:
            Optional[User]: The User object if authentication is successful, otherwise None.
        """
        user = await UserService.get_user_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def is_user_active(db: AsyncSession, user_id: int) -> bool:
        """
        Checks if a user is currently marked as active.

        Args:
            db (AsyncSession): The asynchronous database session.
            user_id (int): The ID of the user.

        Returns:
            bool: True if the user exists and is active, False otherwise.
        """
        user = await UserService.get_user_by_id(db, user_id)
        return user.is_active if user else False