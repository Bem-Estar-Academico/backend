import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.base import Base  # Correct Base import
from app.models import user, notice  # Explicitly import models
from app.models.user import UserType
from app.schemas.user import UserCreate
from app.services.user_service import UserService
from tests.database import TestAsyncSessionLocal, test_engine


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database(event_loop):
    """
    Create the database tables before the test session and drop them after.
    """
    async def setup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    event_loop.run_until_complete(setup())
    yield
    async def teardown():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    event_loop.run_until_complete(teardown())


@pytest.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture to create a new database session for each test, with a transaction
    that is rolled back at the end of the test.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = TestAsyncSessionLocal(bind=connection)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Fixture to create a client for testing the API."""
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client


async def create_user_and_token(
    client: AsyncClient, db_session: AsyncSession, user_data: UserCreate, password: str
) -> str:
    """Helper function to create a user and return an auth token."""
    existing_user = await UserService.get_user_by_email(db_session, user_data.email)
    if not existing_user:
        await UserService.create_user(db_session, user_data)

    login_data = {"username": user_data.email, "password": password}
    response = await client.post("/api/v1/auth/login", data=login_data)
    response.raise_for_status()
    return response.json()["access_token"]


@pytest.fixture
async def coordinator_token(client: AsyncClient, db_session: AsyncSession) -> str:
    """Create a coordinator user and return an auth token."""
    password = "coordpassword"
    user_data = UserCreate(
        email="coordinator.test@example.com",
        full_name="Test Coordinator",
        user_type=UserType.COORDINATOR,
        password=password,
    )
    return await create_user_and_token(client, db_session, user_data, password)


@pytest.fixture
async def social_worker_token(client: AsyncClient, db_session: AsyncSession) -> str:
    """Create a social worker user and return an auth token."""
    password = "swpassword"
    user_data = UserCreate(
        email="socialworker.test@example.com",
        full_name="Test Social Worker",
        user_type=UserType.SOCIAL_WORKER,
        password=password,
    )
    return await create_user_and_token(client, db_session, user_data, password)
