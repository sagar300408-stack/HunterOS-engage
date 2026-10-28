"""
Unit and regression tests for Celery worker event-loop and SQLAlchemy async engine lifecycle.
Specifically tests the fix for process_due_followups_task and loop-bound asyncpg pool safety.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.celery_app import (
    get_worker_event_loop,
    process_due_followups_task,
    shutdown_worker,
)
from app.integrations.postgres import database


def test_get_worker_event_loop_creates_and_persists():
    """Verify that get_worker_event_loop returns an open loop and does not close it."""
    loop1 = get_worker_event_loop()
    assert not loop1.is_closed()
    loop2 = get_worker_event_loop()
    assert loop1 is loop2


def test_get_worker_event_loop_recovers_from_closed_loop():
    """Verify that if a loop was previously closed, a new open loop is created and engine reset."""
    old_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(old_loop)
    old_loop.close()
    assert old_loop.is_closed()

    with patch("app.integrations.postgres.database.reset_engine") as mock_reset:
        new_loop = get_worker_event_loop()
        assert not new_loop.is_closed()
        assert new_loop is not old_loop
        mock_reset.assert_called_once()


def test_process_due_followups_task_repeated_execution():
    """
    Verify process_due_followups_task can be executed repeatedly in the same worker process
    without closing the event loop or causing loop-lifecycle collisions.
    """
    with patch("app.worker.followup_worker.process_due_followups", new_callable=AsyncMock) as mock_followups:
        mock_followups.return_value = True

        # First run
        result1 = process_due_followups_task()
        assert result1 is True
        loop1 = asyncio.get_event_loop()
        assert not loop1.is_closed(), "Event loop must NOT be closed after task execution"

        # Second run
        result2 = process_due_followups_task()
        assert result2 is True
        loop2 = asyncio.get_event_loop()
        assert not loop2.is_closed(), "Event loop must remain open across repeated runs"
        assert loop1 is loop2, "Event loop must be reused across task executions"

        # Third run (queue empty)
        mock_followups.return_value = False
        result3 = process_due_followups_task()
        assert result3 is False
        assert not loop2.is_closed()

        assert mock_followups.call_count == 3


def test_process_due_followups_task_error_logging_and_propagation():
    """Verify that unexpected exceptions in process_due_followups_task are logged and re-raised."""
    with patch("app.worker.followup_worker.process_due_followups", new_callable=AsyncMock) as mock_followups:
        mock_followups.side_effect = RuntimeError("Database connection timed out")

        with pytest.raises(RuntimeError, match="Database connection timed out"):
            process_due_followups_task()


def test_reset_engine_disposes_and_clears_singletons():
    """Verify that reset_engine disposes sync_engine and clears _engine and _session_factory."""
    mock_engine = MagicMock()
    mock_factory = MagicMock()

    database._engine = mock_engine
    database._session_factory = mock_factory

    database.reset_engine()

    mock_engine.sync_engine.dispose.assert_called_once()
    assert database._engine is None
    assert database._session_factory is None


def test_worker_shutdown_signal_triggers_reset_engine():
    """Verify Celery worker_process_shutdown signal calls reset_engine."""
    with patch("app.integrations.postgres.database.reset_engine") as mock_reset:
        shutdown_worker()
        mock_reset.assert_called_once()


@pytest.mark.asyncio
async def test_session_lifecycle_with_engine():
    """Verify get_session context manager opens and closes session properly."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_factory = MagicMock(return_value=mock_session)

    with patch.object(database, "get_session_factory", return_value=mock_factory):
        async with database.get_session() as session:
            assert session is mock_session

        mock_session.close.assert_awaited_once()
