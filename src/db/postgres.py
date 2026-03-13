"""
Async SQLAlchemy engine, session factory, and tenant-aware session context.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from src.core.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


engine: AsyncEngine = create_async_engine(
    settings.postgres_url,
    pool_size=settings.postgres_pool_size,
    max_overflow=settings.postgres_max_overflow,
    echo=(settings.app_env == "development"),
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session(
    tenant_id: UUID | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async session. If tenant_id is provided, sets PostgreSQL
    row-level security context variable ``app.tenant_id``.
    """
    async with async_session_factory() as session:
        if tenant_id:
            await session.execute(
                text("SET LOCAL app.tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables. Use only in dev/test; production uses Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose connection pool on shutdown."""
    await engine.dispose()
