import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.events.model.base_event import UniversalBaseEvent
from app.events.store.models import EventRecord
from app.events.store.repository import EventStoreRepository
from app.events.model.lifecycle import EventLifecycleState

class EventStoreService:
    """
    Coordinates event persistence operations.
    """
    def __init__(self, repository: EventStoreRepository):
        self._repository = repository

    async def persist_event(self, session: AsyncSession, event: UniversalBaseEvent) -> None:
        """
        Converts the universal event model into a database record and persists it.
        """
        # We store the entire payload in JSONB. pydantic's model_dump_json handles serialization of complex types like UUID and datetime
        payload_json = json.loads(event.model_dump_json())

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
            metadata_payload=event.metadata,
            ai_model_version=event.ai_model_version,
            ai_reason=event.ai_reason,
            lifecycle_state=EventLifecycleState.PERSISTED.value,
            retry_count=0
        )
        
        await self._repository.save_event(session, record)
