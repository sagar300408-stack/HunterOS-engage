"""
app/domain/operations/orchestration/port.py

The ExecutionPort interface is the ONLY sanctioned seam between
Phase 3.5 Orchestration and Phase 3.6 Execution.

Rules:
  - Phase 3.5 (ActionOrchestrationEngine) calls submit() exclusively through this interface.
  - Phase 3.6 provides a concrete implementation wired at application startup.
  - No connector logic, credential injection, or external I/O belongs in this file.
  - The NoopExecutionPort stub is used until Phase 3.6 is implemented.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.operations.models import Action


class ExecutionPort(ABC):
    """
    Abstract seam between Phase 3.5 Orchestration and Phase 3.6 Execution.

    Phase 3.6 provides a concrete subclass (e.g. CeleryExecutionPort,
    DirectConnectorPort) and registers it via dependency injection.

    Phase 3.5 remains entirely ignorant of connectors, credentials,
    target systems, or transport mechanisms.
    """

    @abstractmethod
    async def submit(
        self,
        workspace_id: UUID,
        action: Action,
        correlation_id: Optional[UUID] = None,
    ) -> str:
        """
        Submit an EXECUTING Action to the external execution layer.

        Args:
            workspace_id:   Tenant identifier for multi-tenancy enforcement.
            action:         The Action ORM instance in EXECUTING status.
                            All fields (target, parameters in execution_metadata,
                            owner, etc.) are available for routing decisions.
            correlation_id: Optional trace propagation ID.

        Returns:
            execution_handle: An opaque, workspace-scoped string token
                (e.g. a Celery task ID, a job queue ID, a run UUID)
                that Phase 3.5 stores in action.execution_metadata["execution_handle"]
                for downstream tracing by Phase 3.6+.

        Raises:
            Any exception raised here is treated as a Phase 3.5 execution-port
            failure. The ActionOrchestrationEngine will transition the Action
            to FAILED and publish ActionOrchestrationFailedEvent before
            propagating the exception to the caller.
        """
        ...


class NoopExecutionPort(ExecutionPort):
    """
    Stub implementation of ExecutionPort used until Phase 3.6 is available.

    Behaviour:
      - Does NOT perform any I/O, connector calls, or external communication.
      - Returns a deterministic, human-readable handle that encodes the action ID.
      - Safe to use in tests, local development, and CI environments.

    Replace this with a concrete Phase 3.6 adapter before production deployment.
    """

    async def submit(
        self,
        workspace_id: UUID,
        action: Action,
        correlation_id: Optional[UUID] = None,
    ) -> str:
        return f"noop-handle-{action.id}"
