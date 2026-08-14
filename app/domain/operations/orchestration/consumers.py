"""
app/domain/operations/orchestration/consumers.py

Consumes events from the Phase 3.6 legacy ActionEngine and maps them back
to Phase 3.5 Orchestration callbacks.
"""
import logging
from typing import Optional, Tuple
from uuid import UUID

from app.events.bus.event_bus import EventBus
from app.events.model.base_event import UniversalBaseEvent
from app.domain.operations.orchestration.engine import ActionOrchestrationEngine
from app.domain.operations.orchestration.schemas import (
    CompleteOrchestrationRequest,
    FailOrchestrationRequest,
)


logger = logging.getLogger(__name__)


class ActionExecutionResultConsumer:
    """
    Subscribes to ActionEngine events (action.completed, action.failed)
    and reports them back to the ActionOrchestrationEngine using the
    strong identity stored in the idempotency key.
    """

    def __init__(self, orchestration_engine: ActionOrchestrationEngine, event_bus: EventBus):
        self.orchestration_engine = orchestration_engine
        self.event_bus = event_bus

    async def start(self) -> None:
        await self.event_bus.subscribe("action.completed", self.handle_action_completed)
        await self.event_bus.subscribe("action.failed", self.handle_action_failed)

    def _parse_idempotency_key(self, idempotency_key: str) -> Optional[Tuple[UUID, UUID]]:
        """
        Extracts run_id and attempt_id from the idempotency key format:
        '{run_id}:{attempt_id}'
        """
        try:
            parts = idempotency_key.split(":")
            if len(parts) != 2:
                return None
            return UUID(parts[0]), UUID(parts[1])
        except (ValueError, AttributeError):
            return None

    async def handle_action_completed(self, event: UniversalBaseEvent) -> None:
        metadata = event.metadata or {}
        idempotency_key = metadata.get("idempotency_key")
        action_id_str = metadata.get("action_id")
        
        if not idempotency_key or not action_id_str:
            return  # Not an orchestrated action or missing info
            
        parsed = self._parse_idempotency_key(idempotency_key)
        if not parsed:
            return
            
        run_id, attempt_id = parsed
        
        try:
            action_id = UUID(action_id_str)
            
            outcome_data = None
            if "connector_response" in metadata:
                import json
                outcome_data = json.dumps(metadata["connector_response"])
                
            req = CompleteOrchestrationRequest(
                outcome_data=outcome_data,
                correlation_id=event.correlation_id
            )
            
            await self.orchestration_engine.complete(
                workspace_id=event.workspace_id,
                action_id=action_id,
                run_id=run_id,
                req=req
            )
        except Exception as e:
            logger.error(f"Failed to process action.completed callback: {e}", exc_info=True)

    async def handle_action_failed(self, event: UniversalBaseEvent) -> None:
        metadata = event.metadata or {}
        idempotency_key = metadata.get("idempotency_key")
        action_id_str = metadata.get("action_id")
        
        if not idempotency_key or not action_id_str:
            return  # Not an orchestrated action or missing info
            
        parsed = self._parse_idempotency_key(idempotency_key)
        if not parsed:
            return
            
        run_id, attempt_id = parsed
        
        try:
            action_id = UUID(action_id_str)
            req = FailOrchestrationRequest(
                failure_type="EXECUTION_FAILED",
                failure_reason=metadata.get("error_details", "Action failed"),
                retryable=metadata.get("is_retryable", True), # Default to true for phase 3.5 to decide
                correlation_id=event.correlation_id
            )
            
            await self.orchestration_engine.fail(
                workspace_id=event.workspace_id,
                action_id=action_id,
                run_id=run_id,
                req=req
            )
        except Exception as e:
            logger.error(f"Failed to process action.failed callback: {e}", exc_info=True)
