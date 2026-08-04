"""
HunterOS Engage — Diagnostics Startup Validator
app/events/diagnostics/validator.py

Pre-flight startup validator ensuring all diagnostic collectors, health monitors,
snapshot generators, and metric integrations are functional at application startup.
"""

from __future__ import annotations

import asyncio
from app.events.diagnostics.engine import AbstractDiagnosticsEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiagnosticsStartupValidator:
    """
    Validates the Runtime Diagnostics and Live Monitoring subsystem on application startup.
    """

    def __init__(self, engine: AbstractDiagnosticsEngine):
        self.engine = engine

    def validate_sync(self) -> None:
        """
        Synchronous pre-flight validation.
        Runs async checks within the current or a new event loop.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In an already running event loop, schedule task or run basic sync checks
                logger.info("[DiagnosticsStartupValidator] Event loop active; verifying diagnostics engine configuration...")
                assert self.engine is not None, "Diagnostics engine is None"
                assert self.engine.config is not None, "Diagnostics config is None"
                logger.info("[DiagnosticsStartupValidator] ✅ Diagnostics engine configuration verified.")
                return
        except RuntimeError:
            pass

        try:
            asyncio.run(self.validate_async())
        except Exception as exc:
            logger.error(f"[DiagnosticsStartupValidator] Validation failed: {exc}", exc_info=True)
            raise

    async def validate_async(self) -> None:
        """
        Asynchronous pre-flight validation testing complete snapshot generation.
        """
        logger.info("[DiagnosticsStartupValidator] Validating runtime diagnostics collectors and snapshot generator...")
        assert self.engine is not None, "Diagnostics engine is None"

        # Generate a test snapshot
        snapshot = await self.engine.get_runtime_snapshot()
        assert snapshot is not None, "Runtime snapshot generation returned None"
        assert snapshot.snapshot_id is not None, "Runtime snapshot missing snapshot_id"
        assert snapshot.snapshot_timestamp is not None, "Runtime snapshot missing snapshot_timestamp"
        assert snapshot.workers is not None, "Runtime snapshot missing workers"
        assert snapshot.dispatchers is not None, "Runtime snapshot missing dispatchers"
        assert snapshot.queues is not None, "Runtime snapshot missing queues"
        assert snapshot.partitions is not None, "Runtime snapshot missing partitions"
        assert snapshot.locks is not None, "Runtime snapshot missing locks"
        assert snapshot.consumers is not None, "Runtime snapshot missing consumers"
        assert snapshot.scheduler is not None, "Runtime snapshot missing scheduler"
        assert snapshot.health is not None, "Runtime snapshot missing health summary"

        # Verify observation point consistency across sub-reports
        assert snapshot.workers.snapshot_id == snapshot.snapshot_id, "Worker snapshot_id mismatch"
        assert snapshot.dispatchers.snapshot_id == snapshot.snapshot_id, "Dispatcher snapshot_id mismatch"
        assert snapshot.queues.snapshot_id == snapshot.snapshot_id, "Queue snapshot_id mismatch"
        assert snapshot.partitions.snapshot_id == snapshot.snapshot_id, "Partition snapshot_id mismatch"
        assert snapshot.locks.snapshot_id == snapshot.snapshot_id, "Lock snapshot_id mismatch"
        assert snapshot.consumers.snapshot_id == snapshot.snapshot_id, "Consumer snapshot_id mismatch"
        assert snapshot.scheduler.snapshot_id == snapshot.snapshot_id, "Scheduler snapshot_id mismatch"
        assert snapshot.health.snapshot_id == snapshot.snapshot_id, "Health snapshot_id mismatch"

        logger.info(
            f"[DiagnosticsStartupValidator] ✅ Runtime diagnostics platform validated successfully "
            f"(Observation Window: {snapshot.observation_window_ms:.2f}ms, Health Score: {snapshot.health.overall_score})."
        )
