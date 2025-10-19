"""Test database configuration."""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in your .env file for testing")

test_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
