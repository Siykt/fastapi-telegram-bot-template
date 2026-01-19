"""Database initialization and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.utils.snowflake import init_snowflake

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database() -> None:
    """Initialize database engine, session factory, snowflake and sequences."""
    global engine, async_session_factory
    # Use get_settings() to always get current settings (important for env switching)
    settings = get_settings()
    engine = create_async_engine(
        settings.database.get_db_url(),
        echo=settings.database.echo,
        pool_pre_ping=True,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout,
    )
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    init_snowflake()
    # 初始化序列号
    from app.utils.sequence import init_all_sequences
    async with async_session_factory() as session:
        await init_all_sequences(session)


async def close_database() -> None:
    """Close database connections."""
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None

async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency for getting async database session."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@asynccontextmanager
async def get_manual_db_context() -> AsyncGenerator[AsyncSession]:
    """手动管理事务的数据库会话（用于非 FastAPI 场景如 FSM Storage）"""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with async_session_factory() as session:
        yield session
