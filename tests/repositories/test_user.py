from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserType
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate


@pytest.fixture
def db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository():
    return UserRepository()


@pytest.mark.asyncio
async def test_get_by_email(repository, db):
    db.execute = AsyncMock(return_value=MagicMock())
    await repository.get_by_email(db, email="test@test.com")
    db.execute.assert_called_once()


@pytest.mark.asyncio
@patch("app.repositories.user.get_password_hash")
async def test_create(mock_get_password_hash, repository, db):
    mock_get_password_hash.return_value = "hashed_password"
    obj_in = UserCreate(
        email="test@test.com",
        password="password",
        full_name="Test User",
        user_type=UserType.COORDINATOR,
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    await repository.create(db, obj_in=obj_in)
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
@patch("app.repositories.user.get_password_hash")
async def test_update_password(mock_get_password_hash, repository, db):
    mock_get_password_hash.return_value = "new_hashed_password"
    db_obj = User()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    await repository.update_password(db, db_obj=db_obj, new_password="new_password")
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
@patch("app.repositories.user.verify_password")
async def test_authenticate(mock_verify_password, repository, db):
    repository.get_by_email = AsyncMock(
        return_value=User(hashed_password="hashed_password")
    )
    mock_verify_password.return_value = True
    result = await repository.authenticate(
        db, email="test@test.com", password="password"
    )
    assert result is not None

    repository.get_by_email = AsyncMock(return_value=None)
    result = await repository.authenticate(
        db, email="test@test.com", password="password"
    )
    assert result is None

    repository.get_by_email = AsyncMock(
        return_value=User(hashed_password="hashed_password")
    )
    mock_verify_password.return_value = False
    result = await repository.authenticate(
        db, email="test@test.com", password="password"
    )
    assert result is None
