"""
app/domain/operations/orchestration/engine.py

Phase 3.5 — ActionOrchestrationEngine

Responsibility:
    Drive an APPROVED Action through the APPROVED → READY → EXECUTING corridor
    and hand it off to the ExecutionPort (the 3.5/3.6 boundary).

Invariants:
    1. Orchestration only starts from APPROVED — any other status raises OrchestrationError.
    2. revision_id is pinned at governance time; drift raises StalePinnedVersionError.
    3. Readiness is re-evaluated at orchestration time — permanently-failed dependencies
       raise OrchestrationBlockedError; transient blocks raise OrchestrationError.
    4. This engine MUST NOT call external connectors, credentials, or integration adapters.
    5. This engine MUST NOT re-evaluate governance or approval.
    6. Every status transition calls validate_status_transition() (never bypasses state machine),
       action.advance_revision(), and repository.save() before the next step.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select

from app.domain.operations.models import Action, ActionStatus
from app.domain.operations.lifecycle import validate_status_transition
from app.domain.operations.repository import ActionRepository
from app.domain.operations.planning.service import ActionPlanningService
from app.domain.operations.planning.policy import DependencySatisfactionPolicy
from app.domain.operations.orchestration.exceptions import (
    OrchestrationError,
    OrchestrationBlockedError,
    StalePinnedVersionError,
)
from app.domain.operations.orchestration.models import (
    OrchestrationOutcome,
    OrchestrationResult,
    now_utc,
)
from app.domain.operations.orchestration.port import ExecutionPort
from app.domain.operations.orchestration.schemas import OrchestrateActionRequest
from app.domain.operations.exceptions import ActionNotFoundError
from app.events.model.operations_events import (
    ActionOrchestrationStartedEvent,
    ActionOrchestrationHandedOffEvent,
    ActionOrchestrationFailedEvent,
)
from app.events.model.actor_types import ActorType

logger = logging.getLogger(__name__)


class ActionOrchestrationEngine:
    """
    Phase 3.5 Orchestration Engine.

    Wired with:
        repository       — action persistence (read/write).
        planning_service — dependency readiness evaluation.
        execution_port   — abstract 3.5/3.6 boundary; submit() hands off to Phase 3.6.
        event_bus        — transactional outbox for orchestration lifecycle events.
    """

    def __init__(
        self,
        repository: ActionRepository,
        planning_service: ActionPlanningService,
        execution_port: ExecutionPort,
        event_bus: Any,
    ):
        self.repository = repository
        self.planning_service = planning_service
        self.execution_port = execution_port
        self.event_bus = event_bus

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    async def orchestrate(
        self,
        workspace_id: UUID,
        action_id: UUID,
        req: OrchestrateActionRequest,
    ) -> OrchestrationResult:
        """
        Execute the orchestration corridor for a single approved Action.

        Step-by-step:
          1. Fetch Action — ActionNotFoundError if missing.
          2. Status guard — must be APPROVED.
          3. Version guard — revision must match pinned_revision_id.
          4. Re-evaluate readiness — permanent blockers raise OrchestrationBlockedError.
          5. Transition APPROVED → READY.
          6. Publish ActionOrchestrationStartedEvent.
          7. Re-fetch Action (revision advanced).
          8. Transition READY → EXECUTING.
          9. Persist orchestration_started_at in execution_metadata.
         10. Invoke ExecutionPort.submit().
         11. Persist execution_handle in execution_metadata.
         12. Publish ActionOrchestrationHandedOffEvent.
         13. Return OrchestrationResult(HANDED_OFF).

        Any exception raised after step 5 (post-READY) is caught, the Action is
        transitioned to FAILED, ActionOrchestrationFailedEvent is published,
        and the original exception is re-raised.
        """
        # ── Step 1: Fetch ────────────────────────────────────────────────
        action = await self.repository.get_action(workspace_id, action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found in workspace {workspace_id}")

        # ── Step 2: Status guard ─────────────────────────────────────────
        if action.status != ActionStatus.APPROVED:
            raise OrchestrationError(
                f"Action {action_id} must be in APPROVED status to orchestrate, "
                f"but is currently '{action.status.value}'.",
                action_id=action_id,
            )

        # ── Step 3: Version guard ────────────────────────────────────────
        if action.revision_id != req.pinned_revision_id:
            raise StalePinnedVersionError(
                action_id=action_id,
                pinned_revision_id=req.pinned_revision_id,
                current_revision_id=action.revision_id,
            )

        # ── Step 4: Re-evaluate readiness ───────────────────────────────
        await self._assert_readiness(workspace_id, action_id)

        # ── Steps 5-13: READY → EXECUTING corridor ───────────────────────
        # From this point, any failure transitions the Action to FAILED.
        try:
            # Step 5: APPROVED → READY
            action = await self._transition(
                workspace_id=workspace_id,
                action_id=action_id,
                target_status=ActionStatus.READY,
                expected_revision_id=action.revision_id,
                reason="Orchestration: all dependencies satisfied, action ready for execution.",
            )

            # Step 6: Publish orchestration started event
            await self._publish_started_event(workspace_id, action_id, req.pinned_revision_id, req.correlation_id)

            # Step 7: Re-fetch (revision has advanced after READY transition)
            action = await self.repository.get_action(workspace_id, action_id)
            if not action:
                raise ActionNotFoundError(f"Action {action_id} disappeared after READY transition")

            # Step 8: READY → EXECUTING
            action = await self._transition(
                workspace_id=workspace_id,
                action_id=action_id,
                target_status=ActionStatus.EXECUTING,
                expected_revision_id=action.revision_id,
                reason="Orchestration: handing off to execution port.",
            )

            # Step 9: Persist orchestration metadata
            started_at = now_utc()
            meta = dict(action.execution_metadata or {})
            meta["orchestration_started_at"] = started_at.isoformat()
            if req.correlation_id:
                meta["orchestration_correlation_id"] = str(req.correlation_id)
            action.execution_metadata = meta
            action.advance_revision()
            await self.repository.save()

            # Step 10: Invoke ExecutionPort
            handle = await self.execution_port.submit(
                workspace_id=workspace_id,
                action=action,
                correlation_id=req.correlation_id,
            )

            # Step 11: Store execution handle
            meta = dict(action.execution_metadata or {})
            meta["execution_handle"] = handle
            action.execution_metadata = meta
            action.advance_revision()
            await self.repository.save()

            # Step 12: Publish handed-off event
            await self._publish_handed_off_event(workspace_id, action_id, handle, req.correlation_id)

            logger.info(
                "action_orchestration_handed_off",
                extra={
                    "workspace_id": str(workspace_id),
                    "action_id": str(action_id),
                    "execution_handle": handle,
                },
            )

            # Step 13: Return result
            return OrchestrationResult(
                action_id=action_id,
                workspace_id=workspace_id,
                status=OrchestrationOutcome.HANDED_OFF,
                execution_handle=handle,
                reason=None,
                completed_at=now_utc(),
            )

        except Exception as exc:
            await self._handle_failure(workspace_id, action_id, exc, req.correlation_id)
            raise

    # ------------------------------------------------------------------ #
    #  Private helpers
    # ------------------------------------------------------------------ #

    async def _assert_readiness(self, workspace_id: UUID, action_id: UUID) -> None:
        """
        Re-evaluates dependency readiness at orchestration time.
        Raises OrchestrationBlockedError if any dependency is permanently failed.
        Raises OrchestrationError if any dependency is transiently not yet complete.
        """
        readiness = await self.planning_service.evaluate_readiness(workspace_id, action_id)
        if readiness.state == "READY":
            return

        # State is BLOCKED — categorise each blocker
        permanently_failed = []
        transient = []

        if readiness.blockers:
            # Query blocker statuses
            from sqlalchemy import select as sa_select
            stmt = sa_select(Action.id, Action.status).where(Action.id.in_(readiness.blockers))
            result = await self.repository.session.execute(stmt)
            blocker_statuses = {row.id: row.status for row in result.all()}

            for blocker_id in readiness.blockers:
                status = blocker_statuses.get(blocker_id)
                if status is None or DependencySatisfactionPolicy.is_permanently_failed(status):
                    permanently_failed.append(blocker_id)
                else:
                    transient.append(blocker_id)

        if permanently_failed:
            raise OrchestrationBlockedError(
                action_id=action_id,
                permanently_failed_dep_ids=permanently_failed,
            )

        raise OrchestrationError(
            f"Action {action_id} has {len(transient)} transiently-unsatisfied "
            f"dependencies: {transient}. Re-try after prerequisites complete.",
            action_id=action_id,
        )

    async def _transition(
        self,
        workspace_id: UUID,
        action_id: UUID,
        target_status: ActionStatus,
        expected_revision_id: str,
        reason: str,
    ) -> Action:
        """
        Performs a single status transition with all required guards:
          - Fetch current action.
          - Validate revision has not drifted (concurrency guard).
          - Validate the transition is legal via lifecycle state machine.
          - Advance revision and persist.

        Returns the updated Action.
        """
        action = await self.repository.get_action(workspace_id, action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found during transition to {target_status}")

        # Concurrency guard: re-check revision before each transition
        if action.revision_id != expected_revision_id:
            raise StalePinnedVersionError(
                action_id=action_id,
                pinned_revision_id=expected_revision_id,
                current_revision_id=action.revision_id,
            )

        # State machine guard (never bypassed)
        validate_status_transition(action.status, target_status)

        action.status = target_status
        action.advance_revision()
        await self.repository.save()

        logger.info(
            "action_status_transitioned",
            extra={
                "workspace_id": str(workspace_id),
                "action_id": str(action_id),
                "new_status": target_status.value,
                "reason": reason,
            },
        )
        return action

    async def _handle_failure(
        self,
        workspace_id: UUID,
        action_id: UUID,
        exc: Exception,
        correlation_id: Optional[UUID],
    ) -> None:
        """
        Attempts to transition the Action to FAILED and publish the failure event.
        Errors in this handler are logged but NOT propagated — the original
        exception must be allowed to bubble up to the caller.
        """
        try:
            action = await self.repository.get_action(workspace_id, action_id)
            if action and action.status in (ActionStatus.READY, ActionStatus.EXECUTING):
                validate_status_transition(action.status, ActionStatus.FAILED)
                action.status = ActionStatus.FAILED
                action.advance_revision()
                await self.repository.save()

            await self._publish_failed_event(
                workspace_id=workspace_id,
                action_id=action_id,
                failure_reason=str(exc),
                failed_at_status=action.status if action else ActionStatus.APPROVED,
                correlation_id=correlation_id,
            )
        except Exception as inner:
            logger.error(
                "action_orchestration_failure_handler_error",
                extra={
                    "workspace_id": str(workspace_id),
                    "action_id": str(action_id),
                    "original_error": str(exc),
                    "handler_error": str(inner),
                },
            )

    # ------------------------------------------------------------------ #
    #  Event publishing
    # ------------------------------------------------------------------ #

    async def _publish_started_event(
        self,
        workspace_id: UUID,
        action_id: UUID,
        pinned_revision_id: str,
        correlation_id: Optional[UUID],
    ) -> None:
        if not self.event_bus:
            return
        event = ActionOrchestrationStartedEvent(
            workspace_id=workspace_id,
            action_id=action_id,
            pinned_revision_id=pinned_revision_id,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            source_subsystem="orchestration_engine",
        )
        await self.event_bus.publish(event)

    async def _publish_handed_off_event(
        self,
        workspace_id: UUID,
        action_id: UUID,
        execution_handle: str,
        correlation_id: Optional[UUID],
    ) -> None:
        if not self.event_bus:
            return
        event = ActionOrchestrationHandedOffEvent(
            workspace_id=workspace_id,
            action_id=action_id,
            execution_handle=execution_handle,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            source_subsystem="orchestration_engine",
        )
        await self.event_bus.publish(event)

    async def _publish_failed_event(
        self,
        workspace_id: UUID,
        action_id: UUID,
        failure_reason: str,
        failed_at_status: ActionStatus,
        correlation_id: Optional[UUID],
    ) -> None:
        if not self.event_bus:
            return
        event = ActionOrchestrationFailedEvent(
            workspace_id=workspace_id,
            action_id=action_id,
            failure_reason=failure_reason,
            failed_at_status=failed_at_status,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            source_subsystem="orchestration_engine",
        )
        await self.event_bus.publish(event)
