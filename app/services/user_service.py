"""
User service layer for business logic and database operations.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserType, UserUpdate


class UserService:

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_users(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_type: Optional[UserType] = None,
    ) -> List[User]:
        query = select(User).offset(skip).limit(limit)

        if user_type:
            query = query.where(User.user_type == user_type)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        existing_user = await UserService.get_user_by_email(db, user_data.email)

        if existing_user:
            raise ValueError("Email already registered")

        if user_data.user_type == UserType.STUDENT.value:
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
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return False

        await db.delete(user)
        await db.commit()
        return True

    @staticmethod
    async def activate_user(db: AsyncSession, user_id: int) -> Optional[User]:
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
        user = await UserService.get_user_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def is_user_active(db: AsyncSession, user_id: int) -> bool:
        user = await UserService.get_user_by_id(db, user_id)
        return user.is_active if user else False
