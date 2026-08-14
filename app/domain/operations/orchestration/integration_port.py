"""
app/domain/operations/orchestration/integration_port.py

Phase 3.6 implementation of ExecutionPort that wires ActionOrchestrationEngine
to the underlying legacy ActionEngine, bypassing legacy retries.
"""
from typing import Optional
from uuid import UUID

from app.domain.action.engine import ActionEngine
from app.domain.action.schemas import SubmitActionRequest
from app.domain.operations.orchestration.port import ExecutionPort, CancellationResult
from app.domain.operations.orchestration.schemas import ExecutionCommand
from app.domain.action.definitions import action_registry
from app.domain.integration.connectors.registry import connector_registry


class CapabilityError(ValueError):
    pass


class IntegrationExecutionPort(ExecutionPort):
    """
    Connects Phase 3.5 Orchestration to Phase 3.6+ External Execution via ActionEngine.
    """

    def __init__(self, action_engine: ActionEngine):
        self.action_engine = action_engine

    async def submit(self, command: ExecutionCommand) -> str:
        # Resolve connector_id and target_system
        # First, try to get it from the command target
        connector_id = command.target.get("connector_id")
        target_system = command.target.get("target_system")
        
        # If not provided, we try to discover a valid connector
        if not connector_id or not target_system:
            # Validate that the action type exists
            definition = action_registry.get(command.action_type)
            if not definition:
                raise CapabilityError(f"Action type '{command.action_type}' is not registered.")
                
            # Find a connector in the registry that supports this action type
            for connector in connector_registry.get_all_connectors():
                if command.action_type in connector.metadata.supported_actions:
                    connector_id = connector.metadata.connector_id
                    target_system = connector.metadata.connector_type
                    break
                    
            if not connector_id:
                raise CapabilityError(f"No active connector found supporting action '{command.action_type}'.")

        # The idempotency key ensures we never trigger the same orchestration attempt twice
        idempotency_key = f"{command.orchestration_run_id}:{command.orchestration_attempt_id}"

        # is_orchestrated=True ensures ActionEngine does NOT retry internally
        req = SubmitActionRequest(
            connector_id=connector_id,
            target_system=target_system,
            action_type=command.action_type,
            parameters=command.parameters,
            idempotency_key=idempotency_key,
            correlation_id=command.correlation_id,
            requested_by="OrchestrationEngine",
            is_orchestrated=True
        )

        # Handoff to ActionEngine
        execution = await self.action_engine.submit_action(command.workspace_id, req)
        
        # The execution ID becomes the execution_handle that Orchestration tracks
        return str(execution.id)

    async def cancel(
        self,
        workspace_id: UUID,
        execution_handle: str,
        correlation_id: Optional[UUID] = None,
    ) -> CancellationResult:
        """
        Currently the legacy ActionEngine doesn't support active cancellation of running threads easily.
        We return CANCELLATION_UNSUPPORTED for now.
        """
        return CancellationResult.CANCELLATION_UNSUPPORTED
