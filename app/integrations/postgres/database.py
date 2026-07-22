"""
PostgreSQL integration — async engine, session factory, and FastAPI dependency.

Uses SQLAlchemy 2.x async API with asyncpg driver.
Connection pool is configured for production workloads.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_engine = None
_session_factory = None


def get_engine():
    """Return (or lazily create) the shared async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.is_development,    # SQL logging in dev only
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,              # validate connections before use
            pool_recycle=3600,               # recycle connections every hour
        )
        # Log the host portion only — never log credentials
        db_host = settings.database_url.split("@")[-1] if "@" in settings.database_url else "unknown"
        logger.info("database_engine_created", db_host=db_host)
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Return (or lazily create) the async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a managed async database session.

    Automatically commits on success, rolls back on error,
    and always closes the session.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


get_db_session = get_db


from contextlib import asynccontextmanager  # noqa: E402


@asynccontextmanager
async def get_session():
    """
    Async context manager yielding a session — for use outside FastAPI DI.
    Usage:
        async with get_session() as session:
            async with session.begin():
                ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """
    Create all tables from ORM metadata.

    Development only — use Alembic migrations in staging and production.
    """
    from app.config import get_settings
    settings = get_settings()
    
    if not settings.is_development:
        raise RuntimeError(
            "create_tables() is strictly forbidden in production. "
            "Use Alembic migrations instead: `alembic upgrade head`"
        )
        
    # Import all models so their metadata is registered on Base
    from app.domain.conversations.models import Base  # noqa: F401
    from app.domain.customers.models import Customer  # noqa: F401
    from app.domain.memory.models import (  # noqa: F401
        CustomerMemory,
        CustomerMemoryVersion,
        CustomerMemoryEvent,
    )
    from app.domain.intent.models import IntentHistory  # noqa: F401
    from app.domain.security.models import (  # noqa: F401
        User,
        AuditLog,
    )
    from app.domain.dashboard.models import (  # noqa: F401
        PipelineEvent,
        BackgroundJob,
    )
    from app.domain.followup.models import (  # noqa: F401
        FollowUpQueue,
        FollowUpExecution,
        LeadHealthScore,
        SalesMemoryTimeline,
    )

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created", note="development_mode_only")


async def dispose_engine() -> None:
    """Dispose of the engine connection pool on application shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("database_engine_disposed")
        _engine = None
