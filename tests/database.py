"""Test database configuration."""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

if not settings.TEST_DATABASE_URL:
    raise ValueError("TEST_DATABASE_URL must be set in your .env file for testing")

test_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
