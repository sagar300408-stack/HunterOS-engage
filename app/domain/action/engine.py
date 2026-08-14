import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.action.models import ActionExecution, ActionStatus, ActionPriority
from app.domain.action.schemas import SubmitActionRequest, ExecutionResult
from app.domain.action.repository import ActionRepository
from app.domain.action.definitions import action_registry, ExecutionContext
from app.domain.integration.engine import IntegrationEngine
from app.domain.integration.connectors.registry import connector_registry
from app.events.bus.event_bus import EventBus
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType

logger = logging.getLogger(__name__)


class ActionEngine:
    def __init__(self, session: AsyncSession, event_bus: EventBus, integration_engine: IntegrationEngine):
        self.session = session
        self.action_repo = ActionRepository(session)
        self.event_bus = event_bus
        self.integration_engine = integration_engine

    async def submit_action(self, workspace_id: UUID, req: SubmitActionRequest) -> ActionExecution:
        # 1. Idempotency Check
        existing = await self.action_repo.get_by_idempotency_key(workspace_id, req.idempotency_key)
        if existing:
            return existing
            
        # 2. Action Definition Validation
        definition = action_registry.get(req.action_type)
        if not definition:
            raise ValueError(f"Unknown action type: {req.action_type}")
            
        if req.target_system not in definition.supported_connector_types:
            raise ValueError(f"Action {req.action_type} does not support target system {req.target_system}")
            
        definition.validate_parameters(req.parameters)
        
        # 3. Create Action Execution
        action = ActionExecution(
            workspace_id=workspace_id,
            correlation_id=req.correlation_id,
            idempotency_key=req.idempotency_key,
            connector_id=req.connector_id,
            target_system=req.target_system,
            action_type=req.action_type,
            parameters=req.parameters,
            status=ActionStatus.PENDING.value,
            priority=req.priority,
            requested_by=req.requested_by,
            max_retries=0 if req.is_orchestrated else 3
        )
        
        action = await self.action_repo.save_action(action)
        
        await self._publish_event(action, "action.submitted")
        
        # Fire background task
        asyncio.create_task(self._execute(action.id))
        
        return action

    async def _execute(self, action_id: UUID) -> None:
        action = await self.action_repo.get_by_id(action_id)
        if not action:
            return
            
        # Transition to VALIDATING
        action.status = ActionStatus.VALIDATING.value
        action = await self.action_repo.update_action(action)
        await self._publish_event(action, "action.validated")
        
        try:
            # Transition to EXECUTING
            action.status = ActionStatus.EXECUTING.value
            action.started_at = datetime.now(timezone.utc)
            action.queued_duration_ms = int((action.started_at - action.requested_at).total_seconds() * 1000)
            action = await self.action_repo.update_action(action)
            await self._publish_event(action, "action.started")
            
            # Fetch Connector
            connector = connector_registry.get_connector(action.connector_id)
            if not connector:
                raise ValueError(f"Connector {action.connector_id} not registered.")
                
            action.connector_version = connector.metadata.version
            
            # Context
            context = ExecutionContext(
                workspace_id=action.workspace_id,
                action_id=action.id,
                correlation_id=action.correlation_id,
                idempotency_key=action.idempotency_key,
                connector_metadata=connector.metadata
            )
            
            # Execute
            # In a real system, we fetch credentials from integration engine here. For tests, we pass empty dict.
            # E.g. creds = self.integration_engine.cred_provider.retrieve_credentials(conn)
            # For Milestone 9.2 mock, we pass empty.
            result_dict = await connector.execute_action(action.action_type, action.parameters, credentials={})
            
            # Success
            action.completed_at = datetime.now(timezone.utc)
            action.execution_duration_ms = int((action.completed_at - action.started_at).total_seconds() * 1000)
            action.total_duration_ms = action.queued_duration_ms + action.execution_duration_ms
            
            exec_result = ExecutionResult(
                status="success",
                execution_time_ms=action.execution_duration_ms,
                connector_response=result_dict
            )
            
            action.execution_result = exec_result.model_dump()
            action.status = ActionStatus.COMPLETED.value
            action = await self.action_repo.update_action(action)
            await self._publish_event(action, "action.completed")
            
        except Exception as e:
            action.completed_at = datetime.now(timezone.utc)
            if action.started_at:
                action.execution_duration_ms = int((action.completed_at - action.started_at).total_seconds() * 1000)
                action.total_duration_ms = action.queued_duration_ms + action.execution_duration_ms
            
            action.error_details = str(e)
            
            exec_result = ExecutionResult(
                status="error",
                execution_time_ms=action.execution_duration_ms or 0,
                errors=[str(e)]
            )
            action.execution_result = exec_result.model_dump()
            
            action.status = ActionStatus.FAILED.value
            action = await self.action_repo.update_action(action)
            await self._publish_event(action, "action.failed")

    async def _publish_event(self, action: ActionExecution, event_name: str) -> None:
        event = UniversalBaseEvent(
            workspace_id=action.workspace_id,
            category=EventCategory.ACTION,
            event_name=event_name,
            correlation_id=action.correlation_id,
            metadata={
                "action_id": str(action.id),
                "action_type": action.action_type,
                "status": action.status,
                "idempotency_key": action.idempotency_key
            },
            actor_type=ActorType.SYSTEM,
            source_subsystem="action_engine"
        )
        await self.event_bus.publish(event)
