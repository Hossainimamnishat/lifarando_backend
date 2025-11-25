# app/db/session.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


# Example for Docker: postgresql+asyncpg://postgres:postgres@db:5432/food
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# FastAPI dependency
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
