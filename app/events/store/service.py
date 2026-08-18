"""
HunterOS Engage — Event Store Service
app/events/store/service.py

Coordinates event persistence, integrating the Enterprise Idempotency Engine
to guarantee strictly exactly-once publishing semantics.
"""

from __future__ import annotations

import json
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.idempotency.decision import (
    IdempotencyAction,
    IdempotencyConflictError,
    IdempotencyDecision,
)
from app.events.idempotency.engine import IdempotencyEngine
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.lifecycle import EventLifecycleState
from app.events.partitioning.resolver import PartitionResolver
from app.events.priority.priority import PriorityResolver
from app.events.store.models import EventRecord
from app.events.store.repository import EventStoreRepository


class EventStoreService:
    """
    Coordinates event persistence and idempotency evaluation.
    """

    def __init__(
        self,
        repository: EventStoreRepository,
        idempotency_engine: Optional[IdempotencyEngine] = None,
    ) -> None:
        self._repository = repository
        self._idempotency_engine = idempotency_engine or IdempotencyEngine(repository)

    @property
    def idempotency_engine(self) -> IdempotencyEngine:
        return self._idempotency_engine

    @property
    def repository(self) -> EventStoreRepository:
        return self._repository

    async def persist_event(
        self,
        session: AsyncSession,
        event: UniversalBaseEvent,
        is_replay: bool = False,
    ) -> Tuple[Optional[EventRecord], IdempotencyDecision]:
        """
        Evaluates idempotency, converts the domain event model into an EventRecord,
        and persists it to the Event Store within savepoint-isolated error recovery.

        Returns:
            Tuple[Optional[EventRecord], IdempotencyDecision]
        """
        # 1. Evaluate Idempotency
        decision = await self._idempotency_engine.evaluate(
            session=session,
            event=event,
            is_replay=is_replay,
        )

        # 2. If Duplicate detected before persist, return existing record
        if decision.action == IdempotencyAction.DUPLICATE:
            return decision.existing_event, decision

        # 3. Construct EventRecord for persistence
        # payload_json stores the pure domain event without duplicating idempotency_key
        payload_json = json.loads(event.model_dump_json())

        # Metadata payload carries transport metadata (trace_id, idempotency_key, partition_key)
        metadata_dict = dict(event.metadata) if isinstance(event.metadata, dict) else {}
        metadata_dict["idempotency_key"] = decision.key

        trace_id = metadata_dict.get("trace_id") or str(event.correlation_id or event.event_id)
        metadata_dict["trace_id"] = trace_id

        partition_key = PartitionResolver.resolve_partition_key(event)
        metadata_dict["partition_key"] = partition_key

        resolved_priority = PriorityResolver.resolve_priority(event)
        metadata_dict["priority"] = resolved_priority.value

        metadata_payload = json.loads(json.dumps(metadata_dict, default=str))

        record = EventRecord(
            event_id=event.event_id,
            schema_version=event.schema_version,
            occurred_at=event.occurred_at,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            workspace_id=event.workspace_id,
            customer_id=event.customer_id,
            lead_id=event.lead_id,
            conversation_id=event.conversation_id,
            actor_type=event.actor_type.value if hasattr(event.actor_type, "value") else event.actor_type,
            actor_id=event.actor_id,
            source_subsystem=event.source_subsystem,
            category=event.category.value if hasattr(event.category, "value") else event.category,
            event_name=getattr(event, "event_name", "unknown"),
            payload=payload_json,
            metadata_payload=metadata_payload,
            trace_id=trace_id,
            partition_key=partition_key,
            priority=PriorityResolver.get_rank(resolved_priority),
            idempotency_key=decision.key,
            ai_model_version=event.ai_model_version,
            ai_reason=event.ai_reason,
            lifecycle_state=EventLifecycleState.PERSISTED.value,
            retry_count=0,
        )

        # 4. Save with savepoint conflict recovery
        try:
            saved_record = await self._repository.save_event(session, record)
            return saved_record, decision
        except IdempotencyConflictError:
            # Concurrent race caught by DB unique constraint
            race_decision = await self._idempotency_engine.handle_race_conflict(
                session=session,
                key=decision.key,
                event=event,
            )
            return race_decision.existing_event, race_decision
