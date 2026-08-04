"""
HunterOS Engage — Enterprise Idempotency Engine
app/events/idempotency/engine.py

Core engine coordinating deterministic key generation, pre-persist duplicate detection,
concurrency race recovery via savepoint isolation, structured audit logging, and metrics.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.idempotency.decision import IdempotencyAction, IdempotencyDecision
from app.events.idempotency.generator import IdempotencyKeyGenerator
from app.events.observability.metrics import event_metrics

logger = structlog.get_logger(__name__)


class IdempotencyEngine:
    """
    Evaluates incoming event publications against the Event Store to enforce
    strictly exactly-once event persistence semantics.
    """

    def __init__(
        self,
        repository: Any,
        key_generator: Optional[IdempotencyKeyGenerator] = None,
    ) -> None:
        self._repository = repository
        self._generator = key_generator or IdempotencyKeyGenerator()

    @property
    def key_generator(self) -> IdempotencyKeyGenerator:
        return self._generator

    @property
    def repository(self) -> Any:
        return self._repository

    async def evaluate(
        self,
        session: AsyncSession,
        event: Any,
        is_replay: bool = False,
        explicit_key: Optional[str] = None,
    ) -> IdempotencyDecision:
        """
        Evaluates whether an event is unique, a duplicate, or a replay bypass.
        """
        # 1. Derive deterministic idempotency key
        key = self._generator.generate_key(event, explicit_key=explicit_key)

        event_name = getattr(event, "event_name", "unknown")
        event_id = str(getattr(event, "event_id", ""))
        workspace_id = str(getattr(event, "workspace_id", ""))
        correlation_id = str(getattr(event, "correlation_id", "")) if getattr(event, "correlation_id", None) else None

        # 2. Check Replay Bypass
        if is_replay:
            event_metrics.increment("replay_bypasses")
            event_metrics.increment("idempotency_keys_generated")
            logger.info(
                "replay_duplicate_bypass",
                event_name=event_name,
                event_id=event_id,
                workspace_id=workspace_id,
                idempotency_key=key,
                is_replay=True,
            )
            return IdempotencyDecision(
                action=IdempotencyAction.REPLAY_BYPASS,
                key=key,
                reason="Replay operation intentionally bypassed duplicate suppression",
            )

        # 3. Pre-persist lookup with latency timing
        start_time = time.perf_counter()
        existing_record = await self._repository.get_by_idempotency_key(session, key)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        event_metrics.record_idempotency_lookup(duration_ms)
        event_metrics.increment("idempotency_keys_generated")

        # 4. Duplicate Detected
        if existing_record is not None:
            now = datetime.now(timezone.utc)
            created_at = existing_record.occurred_at
            if created_at and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            age_seconds = (now - created_at).total_seconds() if created_at else 0.0

            logger.warning(
                "duplicate_event_detected",
                event_name=event_name,
                incoming_event_id=event_id,
                existing_event_id=str(existing_record.event_id),
                workspace_id=workspace_id,
                idempotency_key=key,
                duplicate_reason="pre_persist_lookup",
                existing_event_state=existing_record.lifecycle_state,
                existing_event_created_at=created_at.isoformat() if created_at else None,
                age_seconds=round(max(0.0, age_seconds), 3),
                trace_id=getattr(existing_record, "trace_id", None),
                correlation_id=correlation_id,
            )

            event_metrics.increment("duplicate_events_blocked")

            return IdempotencyDecision(
                action=IdempotencyAction.DUPLICATE,
                key=key,
                reason="Existing event with same idempotency key found in Event Store",
                existing_event=existing_record,
                lookup_duration_ms=duration_ms,
            )

        # 5. Unique event; ready to persist
        return IdempotencyDecision(
            action=IdempotencyAction.PERSIST,
            key=key,
            reason="Event is unique; ready for Event Store persistence",
            lookup_duration_ms=duration_ms,
        )

    async def handle_race_conflict(
        self,
        session: AsyncSession,
        key: str,
        event: Any,
    ) -> IdempotencyDecision:
        """
        Handles concurrent insert collisions caught by the database unique constraint.
        Called after savepoint rollback so the outer transaction remains valid.
        """
        existing_record = await self._repository.get_by_idempotency_key(session, key)

        event_name = getattr(event, "event_name", "unknown")
        event_id = str(getattr(event, "event_id", ""))
        workspace_id = str(getattr(event, "workspace_id", ""))
        correlation_id = str(getattr(event, "correlation_id", "")) if getattr(event, "correlation_id", None) else None

        now = datetime.now(timezone.utc)
        created_at = existing_record.occurred_at if existing_record else None
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        age_seconds = (now - created_at).total_seconds() if created_at else 0.0

        logger.warning(
            "duplicate_event_detected",
            event_name=event_name,
            incoming_event_id=event_id,
            existing_event_id=str(existing_record.event_id) if existing_record else None,
            workspace_id=workspace_id,
            idempotency_key=key,
            duplicate_reason="concurrency_race",
            existing_event_state=existing_record.lifecycle_state if existing_record else "UNKNOWN",
            existing_event_created_at=created_at.isoformat() if created_at else None,
            age_seconds=round(max(0.0, age_seconds), 3),
            trace_id=getattr(existing_record, "trace_id", None) if existing_record else None,
            correlation_id=correlation_id,
        )

        event_metrics.increment("uniqueness_conflicts")
        event_metrics.increment("duplicate_events_blocked")

        return IdempotencyDecision(
            action=IdempotencyAction.RACE_RECOVERED,
            key=key,
            reason="Concurrent race condition resolved via unique constraint and savepoint recovery",
            existing_event=existing_record,
        )
