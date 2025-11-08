from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Base
from app.repositories.base import BaseRepository


class MockModel(Base):
    __tablename__ = "mock"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class MockSchema(BaseModel):
    name: str


@pytest.fixture
def db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository():
    return BaseRepository(MockModel)


@pytest.mark.asyncio
async def test_get(repository, db):
    db.get = AsyncMock(return_value="result")
    result = await repository.get(db, 1)
    db.get.assert_called_once_with(MockModel, 1)
    assert result == "result"


@pytest.mark.asyncio
async def test_get_multi(repository, db):
    db.execute = AsyncMock(return_value=MagicMock())
    await repository.get_multi(db)
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create(repository, db):
    obj_in = MockSchema(name="test")
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    await repository.create(db, obj_in=obj_in)
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update(repository, db):
    db_obj = MockModel()
    obj_in = MockSchema(name="test")
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    await repository.update(db, db_obj=db_obj, obj_in=obj_in)
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_remove(repository, db):
    repository.get = AsyncMock(return_value="result")
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    result = await repository.remove(db, id=1)
    repository.get.assert_called_once_with(db, 1)
    db.delete.assert_called_once_with("result")
    db.commit.assert_called_once()
    assert result == "result"
