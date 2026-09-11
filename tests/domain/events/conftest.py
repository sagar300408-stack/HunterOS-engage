"""
Wave 2 — Shared pytest fixtures for B7/B8/B9/B10 event certification tests.
All real-PostgreSQL fixtures connect via the production database URL from .env.
"""
import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ── Load .env so DATABASE_URL is available ───────────────────────────────────
import os
from pathlib import Path

_env = Path(__file__).parents[3] / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── Build async URL ───────────────────────────────────────────────────────────
_RAW_URL = os.environ.get("DATABASE_URL", "")
if _RAW_URL.startswith("postgresql://"):
    _ASYNC_URL = _RAW_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _RAW_URL.startswith("postgres://"):
    _ASYNC_URL = _RAW_URL.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    _ASYNC_URL = _RAW_URL  # already async-driver URL


# ── Engine shared for the test session ───────────────────────────────────────
from sqlalchemy.pool import NullPool

@pytest_asyncio.fixture
async def pg_engine():
    engine = create_async_engine(_ASYNC_URL, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
def pg_session_factory(pg_engine):
    return async_sessionmaker(
        bind=pg_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture
async def pg_session(pg_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Yields a real PostgreSQL AsyncSession. Does NOT auto-commit."""
    async with pg_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def patch_global_engine(pg_engine, monkeypatch):
    """
    Ensure that any application code calling get_session() (like _dispatch_async)
    uses our NullPool test engine instead of creating a separate QueuePool engine
    that gets bound to a closed event loop.
    """
    import app.integrations.postgres.database as db
    monkeypatch.setattr(db, "_engine", pg_engine)
    monkeypatch.setattr(db, "_session_factory", None)
    yield



async def _delete_event_store_rows(pg_session_factory, workspace_id: uuid.UUID):
    """Delete all event_store rows for the given workspace — test isolation helper."""
    async with pg_session_factory() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM event_store WHERE workspace_id = :ws"),
                {"ws": str(workspace_id)},
            )
