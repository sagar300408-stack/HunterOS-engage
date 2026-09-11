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
from app.domain.integration.repository import IntegrationRepository
from app.domain.approval.repository import ApprovalRepository
from app.domain.approval.evaluator import PolicyEvaluator

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
        
        # R6.1 Approval Bypass Protection
        if not req.is_orchestrated:
            app_repo = ApprovalRepository(self.session)
            policies = await app_repo.get_all_active_policies(workspace_id)
            
            context_data = {
                "action_type": req.action_type,
                "target_system": req.target_system,
                "risk": req.priority,
            }
            
            class MockActionContext:
                id = None
                status = "READY"
                
            eval_result = PolicyEvaluator.evaluate_policies(policies, MockActionContext(), context_data)
            
            if eval_result.approval_required:
                raise ValueError(f"Action '{req.action_type}' requires approval and cannot be executed directly.")
        
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
        
        # Fire background task via Celery
        from app.domain.action.tasks import execute_action_task
        execute_action_task.apply_async(args=[str(action.id)])
        
        return action

    async def _execute(self, action_id: UUID, celery_task=None) -> None:
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

            # Fetch Integration Connection
            integration_repo = IntegrationRepository(self.session)
            connection = await integration_repo.get_active_connection_by_connector(
                action.workspace_id, action.connector_id
            )
            
            if not connection:
                raise ValueError(f"No active connection found for connector '{action.connector_id}' in this workspace.")
                
            # Fetch Credentials securely
            credentials = self.integration_engine.cred_provider.retrieve_credentials(connection)
            
            if not credentials:
                raise ValueError(f"Credentials missing for connection '{connection.id}'.")
            
            # Context
            context = ExecutionContext(
                workspace_id=action.workspace_id,
                action_id=action.id,
                correlation_id=action.correlation_id,
                idempotency_key=action.idempotency_key,
                connector_metadata=connector.metadata
            )
            
            # Execute
            result_dict = await connector.execute_action(action.action_type, action.parameters, credentials=credentials)
            
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
            is_transient = "timeout" in str(e).lower() or "connection" in str(e).lower() or "rate" in str(e).lower() or "transient" in str(e).lower()
            
            if is_transient and celery_task and celery_task.request.retries < action.max_retries:
                # Retry via Celery
                action.status = ActionStatus.PENDING.value
                await self.action_repo.update_action(action)
                # Exponential backoff
                delay = 2 ** celery_task.request.retries * 5
                raise celery_task.retry(exc=e, countdown=delay)

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
