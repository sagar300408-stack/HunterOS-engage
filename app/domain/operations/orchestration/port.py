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

import enum
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.operations.orchestration.schemas import ExecutionCommand


class CancellationResult(str, enum.Enum):
    SUPPORTED_ACCEPTED = "SUPPORTED_ACCEPTED"
    SUPPORTED_REJECTED = "SUPPORTED_REJECTED"
    CANCELLATION_UNSUPPORTED = "CANCELLATION_UNSUPPORTED"


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
        command: ExecutionCommand,
    ) -> str:
        """
        Submit an EXECUTING Action to the external execution layer.

        Args:
            command:        The Explicit Execution Command holding workspace, action,
                            run, attempt, target, and parameters.

        Returns:
            execution_handle: An opaque, workspace-scoped string token
                (e.g. a Celery task ID, a job queue ID, a run UUID)
                that Phase 3.5 stores in attempt.execution_handle
                for downstream tracing by Phase 3.6+.
        """
        ...

    @abstractmethod
    async def cancel(
        self,
        workspace_id: UUID,
        execution_handle: str,
        correlation_id: Optional[UUID] = None,
    ) -> CancellationResult:
        """
        Request cancellation of an executing external operation.
        """
        ...


class NoopExecutionPort(ExecutionPort):
    """
    Stub implementation of ExecutionPort used until Phase 3.6 is available.
    """

    async def submit(
        self,
        command: ExecutionCommand,
    ) -> str:
        return f"noop-handle-{command.action_id}-{command.orchestration_attempt_id}"

    async def cancel(
        self,
        workspace_id: UUID,
        execution_handle: str,
        correlation_id: Optional[UUID] = None,
    ) -> CancellationResult:
        # Stub implementation doesn't support actual cancellation
        return CancellationResult.CANCELLATION_UNSUPPORTED
