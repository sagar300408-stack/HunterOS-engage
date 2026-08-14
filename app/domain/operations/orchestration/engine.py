"""
app/domain/operations/orchestration/engine.py

Phase 3.5 — ActionOrchestrationEngine
"""

import logging
from typing import Any, Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.domain.operations.models import Action, ActionStatus
from app.domain.operations.lifecycle import validate_status_transition
from app.domain.operations.repository import ActionRepository
from app.domain.operations.planning.service import ActionPlanningService
from app.domain.operations.planning.policy import DependencySatisfactionPolicy
from app.domain.operations.orchestration.exceptions import (
    OrchestrationError,
    OrchestrationBlockedError,
    StalePinnedVersionError,
    RetryLimitExceededError,
    InvalidOrchestrationStateError
)
from app.domain.operations.orchestration.models import (
    OrchestrationRun,
    OrchestrationAttempt,
    OrchestrationRunState,
    OrchestrationAttemptState
)
from app.domain.operations.orchestration.port import ExecutionPort, CancellationResult
from app.domain.operations.orchestration.schemas import (
    OrchestrateActionRequest,
    RetryOrchestrationRequest,
    CancelOrchestrationRequest,
    CompleteOrchestrationRequest,
    FailOrchestrationRequest,
    TimeoutOrchestrationRequest,
    OrchestrationRunDTO,
    OrchestrationAttemptDTO,
    ExecutionCommand
)
from app.domain.operations.exceptions import ActionNotFoundError
from app.events.model.operations_events import (
    ActionOrchestrationRunStartedEvent,
    ActionOrchestrationRunCompletedEvent,
    ActionOrchestrationRunFailedEvent,
    ActionOrchestrationRunTimedOutEvent,
    ActionOrchestrationRunCancelledEvent,
    ActionStatusChangedEvent
)
from app.events.model.actor_types import ActorType

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ActionOrchestrationEngine:
    def __init__(
        self,
        session: AsyncSession,
        repository: ActionRepository,
        planning_service: ActionPlanningService,
        execution_port: ExecutionPort,
        event_bus: Any,
    ):
        self.session = session
        self.repository = repository
        self.planning_service = planning_service
        self.execution_port = execution_port
        self.event_bus = event_bus
        self.max_retries = get_settings().orchestration_max_retries

    async def orchestrate(
        self,
        workspace_id: UUID,
        action_id: UUID,
        req: OrchestrateActionRequest,
    ) -> OrchestrationRunDTO:
        # Step 1: Fetch Action
        action = await self.repository.get_action(workspace_id, action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found.")

        if action.status != ActionStatus.APPROVED:
            raise OrchestrationError(
                f"Action {action_id} must be in APPROVED status to orchestrate.",
                action_id=action_id
            )

        if action.version_number != req.pinned_action_version:
            raise StalePinnedVersionError(
                action_id, req.pinned_action_version, action.version_number
            )

        # Step 2: Idempotency Check
        stmt = select(OrchestrationRun).options(selectinload(OrchestrationRun.attempts)).where(
            OrchestrationRun.workspace_id == workspace_id,
            OrchestrationRun.action_id == action_id,
            OrchestrationRun.state.in_([
                OrchestrationRunState.CREATED,
                OrchestrationRunState.READY,
                OrchestrationRunState.STARTING,
                OrchestrationRunState.EXECUTING
            ])
        )
        result = await self.session.execute(stmt)
        active_run = result.scalar_one_or_none()

        if active_run:
            if active_run.action_version != req.pinned_action_version:
                raise StalePinnedVersionError(
                    action_id, active_run.action_version, req.pinned_action_version
                )
            return self._to_dto(active_run)

        # Step 3: Readiness Validation
        await self._assert_readiness(workspace_id, action_id)

        # Step 4: Transition to READY if APPROVED
        if action.status == ActionStatus.APPROVED:
            validate_status_transition(action.status, ActionStatus.READY)
            old_status = action.status
            action.status = ActionStatus.READY
            action.advance_revision()
            
            # Re-fetch action for safety (simulating locking/concurrency checks in a real app)
            action = await self.repository.get_action(workspace_id, action_id)
            if not action or action.status != ActionStatus.READY:
                # If concurrent modification changed it
                pass 
                
            if action.version_number != req.pinned_action_version:
                raise StalePinnedVersionError(
                    action_id, req.pinned_action_version, action.version_number
                )
                
        # Step 5: Create OrchestrationRun & Attempt
        run = OrchestrationRun(
            workspace_id=workspace_id,
            action_id=action_id,
            action_version=action.version_number,
            state=OrchestrationRunState.EXECUTING,
            max_attempts=self.max_retries + 1,
            attempt_count=1
        )
        self.session.add(run)

        attempt = OrchestrationAttempt(
            run=run,
            attempt_number=1,
            state=OrchestrationAttemptState.EXECUTING,
            correlation_id=req.correlation_id,
            started_at=now_utc()
        )
        self.session.add(attempt)

        # Step 6: Transition Action to EXECUTING
        validate_status_transition(action.status, ActionStatus.EXECUTING)
        old_status = action.status
        action.status = ActionStatus.EXECUTING
        action.advance_revision()
        
        # Step 6: Publish Events
        if self.event_bus:
            await self.event_bus.publish(ActionOrchestrationRunStartedEvent(
                workspace_id=workspace_id,
                action_id=action_id,
                run_id=run.id,
                action_version=action.version_number,
                correlation_id=req.correlation_id,
                actor_type=ActorType.SYSTEM,
                source_subsystem="orchestration_engine"
            ))
            await self.event_bus.publish(ActionStatusChangedEvent(
                workspace_id=workspace_id,
                action_id=action_id,
                old_status=old_status,
                new_status=action.status,
                reason="Orchestration started",
                correlation_id=req.correlation_id,
                actor_type=ActorType.SYSTEM,
                source_subsystem="orchestration_engine"
            ))

        await self.session.commit()

        # Step 7: Handoff to ExecutionPort
        command = ExecutionCommand(
            workspace_id=workspace_id,
            action_id=action_id,
            action_version=action.version_number,
            action_type=action.action_type,
            target=action.target,
            parameters=action.execution_metadata.get("parameters", {}),
            orchestration_run_id=run.id,
            orchestration_attempt_id=attempt.id,
            correlation_id=req.correlation_id
        )
        try:
            handle = await self.execution_port.submit(command)
            attempt.execution_handle = handle
            self.session.add(attempt)
            await self.session.commit()
        except Exception as e:
            # Synchronous failure during handoff
            await self._handle_attempt_failure(run, attempt, str(e), action, req.correlation_id, retryable=True)

        return self._to_dto(run)

    async def retry(
        self,
        workspace_id: UUID,
        action_id: UUID,
        run_id: UUID,
        req: RetryOrchestrationRequest
    ) -> OrchestrationRunDTO:
        # Step 1: Fetch Run and Action
        run, action = await self._fetch_run_and_action(workspace_id, action_id, run_id)

        # Step 2: Validate Governance & Version
        if action.status != ActionStatus.EXECUTING:
             # Action must be in EXECUTING for run to be active/retryable
             pass # Or re-verify approval via planning service? We pin action version, so if version changed, it's stale.

        if run.action_version != action.version_number:
            raise StalePinnedVersionError(action_id, run.action_version, action.version_number)

        # Step 3: Validate Run State
        if run.state != OrchestrationRunState.FAILED:
            raise InvalidOrchestrationStateError(action_id, run_id, run.state.value, "retry")

        # Step 4: Validate Limits
        if run.attempt_count >= run.max_attempts:
            raise RetryLimitExceededError(action_id, run_id, run.max_attempts)

        # Step 5: Execute Retry
        run.attempt_count += 1
        run.state = OrchestrationRunState.EXECUTING
        run.updated_at = now_utc()
        self.session.add(run)

        attempt = OrchestrationAttempt(
            run=run,
            attempt_number=run.attempt_count,
            state=OrchestrationAttemptState.EXECUTING,
            correlation_id=req.correlation_id,
            started_at=now_utc()
        )
        self.session.add(attempt)

        if self.event_bus:
            await self.event_bus.publish(ActionOrchestrationRunStartedEvent(
                workspace_id=workspace_id,
                action_id=action_id,
                run_id=run.id,
                action_version=action.version_number,
                correlation_id=req.correlation_id,
                actor_type=ActorType.SYSTEM,
                source_subsystem="orchestration_engine"
            ))

        await self.session.commit()

        # Step 6: Handoff
        command = ExecutionCommand(
            workspace_id=workspace_id,
            action_id=action_id,
            action_version=action.version_number,
            action_type=action.action_type,
            target=action.target,
            parameters=action.execution_metadata.get("parameters", {}),
            orchestration_run_id=run.id,
            orchestration_attempt_id=attempt.id,
            correlation_id=req.correlation_id
        )
        try:
            handle = await self.execution_port.submit(command)
            attempt.execution_handle = handle
            self.session.add(attempt)
            await self.session.commit()
        except Exception as e:
            await self._handle_attempt_failure(run, attempt, str(e), action, req.correlation_id, retryable=True)

        return self._to_dto(run)

    async def cancel(
        self,
        workspace_id: UUID,
        action_id: UUID,
        run_id: UUID,
        req: CancelOrchestrationRequest
    ) -> OrchestrationRunDTO:
        run, action = await self._fetch_run_and_action(workspace_id, action_id, run_id)

        if run.state not in [OrchestrationRunState.READY, OrchestrationRunState.STARTING, OrchestrationRunState.EXECUTING]:
            return self._to_dto(run) # Idempotent if already terminated

        active_attempt = next((a for a in run.attempts if a.state == OrchestrationAttemptState.EXECUTING), None)
        
        if active_attempt and active_attempt.execution_handle:
            cancel_result = await self.execution_port.cancel(workspace_id, active_attempt.execution_handle, req.correlation_id)
            
            if cancel_result == CancellationResult.CANCELLATION_UNSUPPORTED:
                # Cannot cancel execution, state remains EXECUTING
                return self._to_dto(run)
        
        # Cancellation Supported & Accepted
        if active_attempt:
            active_attempt.state = OrchestrationAttemptState.CANCELLED
            active_attempt.completed_at = now_utc()
            self.session.add(active_attempt)

        run.state = OrchestrationRunState.CANCELLED
        run.updated_at = now_utc()
        self.session.add(run)

        # NOTE: Orchestration CANCELLED -> Action CANCELLED is not automatic.
        # But if the action cancellation triggered this, action handles its own state.
        
        if self.event_bus:
            await self.event_bus.publish(ActionOrchestrationRunCancelledEvent(
                workspace_id=workspace_id,
                action_id=action_id,
                run_id=run.id,
                action_version=action.version_number,
                correlation_id=req.correlation_id,
                actor_type=ActorType.SYSTEM,
                source_subsystem="orchestration_engine"
            ))

        await self.session.commit()
        return self._to_dto(run)

    async def complete(
        self,
        workspace_id: UUID,
        action_id: UUID,
        run_id: UUID,
        req: CompleteOrchestrationRequest
    ) -> OrchestrationRunDTO:
        run, action = await self._fetch_run_and_action(workspace_id, action_id, run_id)

        if run.state not in [OrchestrationRunState.EXECUTING]:
            raise InvalidOrchestrationStateError(action_id, run_id, run.state.value, "complete")
            
        if run.action_version != action.version_number:
            raise StalePinnedVersionError(action_id, run.action_version, action.version_number)

        active_attempt = next((a for a in run.attempts if a.state == OrchestrationAttemptState.EXECUTING), None)
        if active_attempt:
            active_attempt.state = OrchestrationAttemptState.COMPLETED
            active_attempt.outcome = req.outcome_data
            active_attempt.completed_at = now_utc()
            self.session.add(active_attempt)

        run.state = OrchestrationRunState.COMPLETED
        run.updated_at = now_utc()
        self.session.add(run)

        # Transition Action to COMPLETED
        validate_status_transition(action.status, ActionStatus.COMPLETED)
        old_status = action.status
        action.status = ActionStatus.COMPLETED
        action.advance_revision()

        if self.event_bus:
            await self.event_bus.publish(ActionOrchestrationRunCompletedEvent(
                workspace_id=workspace_id,
                action_id=action_id,
                run_id=run.id,
                action_version=action.version_number,
                correlation_id=req.correlation_id,
                actor_type=ActorType.SYSTEM,
                source_subsystem="orchestration_engine"
            ))
            await self.event_bus.publish(ActionStatusChangedEvent(
                workspace_id=workspace_id,
                action_id=action_id,
                old_status=old_status,
                new_status=ActionStatus.COMPLETED,
                reason="Orchestration completed",
                correlation_id=req.correlation_id,
                actor_type=ActorType.SYSTEM,
                source_subsystem="orchestration_engine"
            ))

        await self.session.commit()
        return self._to_dto(run)

    async def fail(
        self,
        workspace_id: UUID,
        action_id: UUID,
        run_id: UUID,
        req: FailOrchestrationRequest
    ) -> OrchestrationRunDTO:
        run, action = await self._fetch_run_and_action(workspace_id, action_id, run_id)

        if run.state not in [OrchestrationRunState.EXECUTING]:
            raise InvalidOrchestrationStateError(action_id, run_id, run.state.value, "fail")

        active_attempt = next((a for a in run.attempts if a.state == OrchestrationAttemptState.EXECUTING), None)
        if active_attempt:
            active_attempt.failure_type = req.failure_type
            self.session.add(active_attempt)
            
            await self._handle_attempt_failure(
                run, active_attempt, req.failure_reason, action, req.correlation_id, req.retryable
            )

        return self._to_dto(run)

    async def timeout(
        self,
        workspace_id: UUID,
        action_id: UUID,
        run_id: UUID,
        req: TimeoutOrchestrationRequest
    ) -> OrchestrationRunDTO:
        run, action = await self._fetch_run_and_action(workspace_id, action_id, run_id)

        if run.state not in [OrchestrationRunState.EXECUTING]:
            raise InvalidOrchestrationStateError(action_id, run_id, run.state.value, "timeout")

        active_attempt = next((a for a in run.attempts if a.state == OrchestrationAttemptState.EXECUTING), None)
        if active_attempt:
            active_attempt.state = OrchestrationAttemptState.TIMED_OUT
            active_attempt.completed_at = now_utc()
            self.session.add(active_attempt)

        run.state = OrchestrationRunState.TIMED_OUT
        run.updated_at = now_utc()
        self.session.add(run)

        # Note: Action status remains EXECUTING per Plan #9
        if self.event_bus:
            await self.event_bus.publish(ActionOrchestrationRunTimedOutEvent(
                workspace_id=workspace_id,
                action_id=action_id,
                run_id=run.id,
                action_version=action.version_number,
                correlation_id=req.correlation_id,
                actor_type=ActorType.SYSTEM,
                source_subsystem="orchestration_engine"
            ))

        await self.session.commit()
        return self._to_dto(run)

    # ------------------------------------------------------------------ #
    #  Private helpers
    # ------------------------------------------------------------------ #

    async def _fetch_run_and_action(self, workspace_id: UUID, action_id: UUID, run_id: UUID):
        stmt = select(OrchestrationRun).options(selectinload(OrchestrationRun.attempts)).where(
            OrchestrationRun.workspace_id == workspace_id,
            OrchestrationRun.action_id == action_id,
            OrchestrationRun.id == run_id
        )
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        
        if not run:
            raise OrchestrationError(f"Run {run_id} not found.", action_id)
            
        action = await self.repository.get_action(workspace_id, action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found.")

        return run, action

    async def _handle_attempt_failure(
        self,
        run: OrchestrationRun,
        attempt: OrchestrationAttempt,
        reason: str,
        action: Action,
        correlation_id: Optional[UUID],
        retryable: bool
    ):
        attempt.state = OrchestrationAttemptState.FAILED
        attempt.failure_reason = reason
        attempt.retryable = retryable
        attempt.completed_at = now_utc()
        self.session.add(attempt)

        if not retryable or run.attempt_count >= run.max_attempts:
            # Terminal Failure
            run.state = OrchestrationRunState.FAILED
            run.failure_reason = reason
            run.updated_at = now_utc()
            self.session.add(run)
            
            # Map Orchestration FAILED -> Action FAILED
            validate_status_transition(action.status, ActionStatus.FAILED)
            old_status = action.status
            action.status = ActionStatus.FAILED
            action.advance_revision()
            
            if self.event_bus:
                await self.event_bus.publish(ActionOrchestrationRunFailedEvent(
                    workspace_id=run.workspace_id,
                    action_id=run.action_id,
                    run_id=run.id,
                    action_version=run.action_version,
                    failure_reason=reason,
                    correlation_id=correlation_id,
                    actor_type=ActorType.SYSTEM,
                    source_subsystem="orchestration_engine"
                ))
                await self.event_bus.publish(ActionStatusChangedEvent(
                    workspace_id=run.workspace_id,
                    action_id=run.action_id,
                    old_status=old_status,
                    new_status=ActionStatus.FAILED,
                    reason=reason,
                    correlation_id=correlation_id,
                    actor_type=ActorType.SYSTEM,
                    source_subsystem="orchestration_engine"
                ))
        else:
            # Retryable Failure -> Run becomes FAILED (but can be retried)
            run.state = OrchestrationRunState.FAILED
            run.updated_at = now_utc()
            self.session.add(run)
            
            # Note: Action status remains EXECUTING
            if self.event_bus:
                await self.event_bus.publish(ActionOrchestrationRunFailedEvent(
                    workspace_id=run.workspace_id,
                    action_id=run.action_id,
                    run_id=run.id,
                    action_version=run.action_version,
                    failure_reason=reason,
                    correlation_id=correlation_id,
                    actor_type=ActorType.SYSTEM,
                    source_subsystem="orchestration_engine"
                ))
                
        await self.session.commit()

    async def _assert_readiness(self, workspace_id: UUID, action_id: UUID) -> None:
        readiness = await self.planning_service.evaluate_readiness(workspace_id, action_id)
        if readiness.state == "READY":
            return

        permanently_failed = []
        transient = []

        if readiness.blockers:
            stmt = select(Action.id, Action.status).where(Action.id.in_(readiness.blockers))
            result = await self.session.execute(stmt)
            blocker_statuses = {row.id: row.status for row in result.all()}

            for blocker_id in readiness.blockers:
                status = blocker_statuses.get(blocker_id)
                if status is None or DependencySatisfactionPolicy.is_permanently_failed(status):
                    permanently_failed.append(blocker_id)
                else:
                    transient.append(blocker_id)

        if permanently_failed:
            raise OrchestrationBlockedError(action_id, permanently_failed)

        raise OrchestrationError(
            f"Action {action_id} has {len(transient)} transiently-unsatisfied blockers.",
            action_id=action_id,
        )

    def _to_dto(self, run: OrchestrationRun) -> OrchestrationRunDTO:
        attempts_dto = []
        for a in run.attempts:
            attempts_dto.append(OrchestrationAttemptDTO(
                id=a.id,
                run_id=a.run_id,
                attempt_number=a.attempt_number,
                state=a.state.value,
                execution_handle=a.execution_handle,
                outcome=a.outcome,
                failure_type=a.failure_type,
                failure_reason=a.failure_reason,
                retryable=a.retryable,
                started_at=a.started_at,
                completed_at=a.completed_at
            ))
            
        return OrchestrationRunDTO(
            id=run.id,
            action_id=run.action_id,
            workspace_id=run.workspace_id,
            action_version=run.action_version,
            state=run.state.value,
            attempt_count=run.attempt_count,
            max_attempts=run.max_attempts,
            failure_reason=run.failure_reason,
            created_at=run.created_at,
            updated_at=run.updated_at,
            attempts=attempts_dto
        )
