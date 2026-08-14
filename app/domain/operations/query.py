from typing import List, Optional, Tuple, Any
from uuid import UUID
from datetime import datetime, timezone
import logging

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.operations.models import Action, ActionStatus
from app.domain.approval.models import ApprovalRequest, ApprovalStatus
from app.domain.operations.orchestration.models import OrchestrationRun, OrchestrationAttempt, OrchestrationRunState, OrchestrationAttemptState
from app.domain.action.models import ActionExecution, ActionStatus as ExecutionStatus

from app.domain.operations.schemas import (
    OperationalContextDTO,
    ActionSummaryDTO,
    ActionReadiness,
    GovernanceSummaryDTO,
    OrchestrationSummaryDTO,
    ExecutionSummaryDTO,
    AttentionSignalDTO
)
from app.domain.operations.planning.service import ActionPlanningService
from app.domain.operations.exceptions import ActionNotFoundError


class OperationalQueryService:
    """
    Phase 3.7 Operational Integration Layer (Query Boundary).
    This service performs live composition of authoritative operational state
    without maintaining a secondary persistent projection.
    It strictly adheres to Phase 3.1 - 3.6 domain semantics for "current" state.
    """

    def __init__(self, session: AsyncSession, planning_service: ActionPlanningService):
        self.session = session
        self.planning_service = planning_service

    async def get_operational_context(self, workspace_id: UUID, action_id: UUID) -> OperationalContextDTO:
        # 1. ACTION STATE
        stmt_action = select(Action).where(Action.workspace_id == workspace_id, Action.id == action_id)
        result_action = await self.session.execute(stmt_action)
        action = result_action.scalars().first()
        
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found in workspace {workspace_id}")

        action_summary = ActionSummaryDTO(
            action_id=action.id,
            action_type=action.action_type,
            status=action.status,
            priority=action.priority,
            version=action.version_number,
            created_at=action.created_at.isoformat()
        )

        # 2. READINESS (Phase 3.3 Semantic Boundary)
        readiness: ActionReadiness = await self.planning_service.evaluate_readiness(workspace_id, action_id)

        # 3. GOVERNANCE
        stmt_approval = (
            select(ApprovalRequest)
            .where(ApprovalRequest.workspace_id == workspace_id, ApprovalRequest.action_id == action_id)
            .where(ApprovalRequest.action_version == action.version_number)
            .order_by(ApprovalRequest.requested_at.desc())
            .limit(1)
        )
        approval_req = (await self.session.execute(stmt_approval)).scalars().first()
        
        governance_summary = GovernanceSummaryDTO(
            approval_required=bool(approval_req),
            approval_status=approval_req.status if approval_req else None,
            approval_request_id=approval_req.id if approval_req else None,
            stale_authorization=False  # Handled by matching action_version above
        )
        
        # Check if there is an older approval that is stale
        if not approval_req:
            stmt_stale = (
                select(ApprovalRequest.id)
                .where(ApprovalRequest.workspace_id == workspace_id, ApprovalRequest.action_id == action_id)
                .limit(1)
            )
            has_any = (await self.session.execute(stmt_stale)).scalar()
            if has_any:
                governance_summary = GovernanceSummaryDTO(
                    approval_required=True,
                    approval_status=None,
                    approval_request_id=None,
                    stale_authorization=True
                )

        # 4. ORCHESTRATION
        stmt_run = (
            select(OrchestrationRun)
            .where(OrchestrationRun.workspace_id == workspace_id, OrchestrationRun.action_id == action_id)
            .where(OrchestrationRun.action_version == action.version_number)
            .order_by(OrchestrationRun.created_at.desc())
            .limit(1)
        )
        run = (await self.session.execute(stmt_run)).scalars().first()
        
        orchestration_summary = OrchestrationSummaryDTO(
            run_id=run.id if run else None,
            state=run.state if run else None,
            attempt_count=run.attempt_count if run else 0
        )

        # 5. ATTEMPT & EXECUTION
        execution_summary = ExecutionSummaryDTO()
        if run:
            stmt_attempt = (
                select(OrchestrationAttempt)
                .where(OrchestrationAttempt.run_id == run.id)
                .order_by(OrchestrationAttempt.attempt_number.desc())
                .limit(1)
            )
            attempt = (await self.session.execute(stmt_attempt)).scalars().first()
            
            if attempt:
                # Look up execution via idempotency_key (run_id:attempt_number)
                idemp_key = f"{run.id}:{attempt.attempt_number}"
                stmt_exec = (
                    select(ActionExecution)
                    .where(ActionExecution.workspace_id == workspace_id)
                    .where(ActionExecution.idempotency_key == idemp_key)
                )
                execution = (await self.session.execute(stmt_exec)).scalars().first()
                
                execution_summary = ExecutionSummaryDTO(
                    execution_handle=attempt.execution_handle,
                    state=execution.status if execution else attempt.state,
                    failure_classification=execution.error_details if execution else attempt.failure_type,
                    retryable=attempt.retryable,
                    completed_at=execution.completed_at.isoformat() if execution and execution.completed_at else None
                )

        # 6. ATTENTION SIGNALS (Deterministic)
        signals = []
        if readiness.state == "BLOCKED":
            signals.append(AttentionSignalDTO(code="BLOCKED_BY_DEPENDENCY", severity="high", reason="Missing prerequisites", source="planning"))
        if governance_summary.approval_status == "REJECTED":
            signals.append(AttentionSignalDTO(code="APPROVAL_REJECTED", severity="critical", reason="Action approval rejected", source="governance"))
        if governance_summary.stale_authorization:
            signals.append(AttentionSignalDTO(code="STALE_AUTHORIZATION", severity="high", reason="Action modified since approval", source="governance"))
        if orchestration_summary.state == OrchestrationRunState.FAILED:
            signals.append(AttentionSignalDTO(code="ORCHESTRATION_FAILED", severity="critical", reason="Run failed permanently", source="orchestration"))
        if orchestration_summary.state == OrchestrationRunState.TIMED_OUT:
            signals.append(AttentionSignalDTO(code="ORCHESTRATION_TIMED_OUT", severity="critical", reason="Run timed out", source="orchestration"))
        if execution_summary.state == ExecutionStatus.FAILED:
            signals.append(AttentionSignalDTO(code="EXECUTION_FAILED", severity="high", reason="Current execution attempt failed", source="execution"))

        return OperationalContextDTO(
            workspace_id=workspace_id,
            action=action_summary,
            readiness=readiness,
            governance=governance_summary,
            orchestration=orchestration_summary,
            execution=execution_summary,
            attention_signals=signals,
            evaluated_at=datetime.now(timezone.utc).isoformat()
        )

    async def get_workspace_operational_summary(self, workspace_id: UUID) -> dict:
        """
        Uses SQL aggregations to compute summary metrics from their authoritative sources.
        """
        # Active Actions: DETECTED, PLANNED, READY, PENDING_APPROVAL, APPROVED
        active_statuses = [
            ActionStatus.DETECTED, ActionStatus.PLANNED, ActionStatus.READY, 
            ActionStatus.PENDING_APPROVAL, ActionStatus.APPROVED
        ]
        stmt_active = select(func.count(Action.id)).where(Action.workspace_id == workspace_id, Action.status.in_(active_statuses))
        active_count = (await self.session.execute(stmt_active)).scalar() or 0

        # Blocked Actions: derived from Phase 3.3 Readiness via Dependency graph
        # This is a bit complex for a simple COUNT without duplicating readiness logic.
        # However, to be strictly correct with the rule: "BLOCKED -> Phase 3.3 readiness"
        # We find actions that have dependencies which are NOT satisfied.
        stmt_blocked = text("""
            SELECT COUNT(DISTINCT a.id)
            FROM actions a
            JOIN action_dependencies ad ON a.id = ad.action_id
            JOIN actions dep ON ad.depends_on_action_id = dep.id
            WHERE a.workspace_id = :workspace_id
              AND a.status IN ('DETECTED', 'PLANNED', 'READY')
              AND dep.status NOT IN ('COMPLETED', 'CANCELLED')
        """)
        blocked_count = (await self.session.execute(stmt_blocked.bindparams(workspace_id=workspace_id))).scalar() or 0

        # Pending Approval: Phase 3.4 Governance
        stmt_pending = select(func.count(ApprovalRequest.id)).where(
            ApprovalRequest.workspace_id == workspace_id, 
            ApprovalRequest.status.in_([ApprovalStatus.PENDING.value, ApprovalStatus.UNDER_REVIEW.value])
        )
        pending_count = (await self.session.execute(stmt_pending)).scalar() or 0

        # Executing: Phase 3.5 Orchestration
        stmt_exec = select(func.count(OrchestrationRun.id)).where(
            OrchestrationRun.workspace_id == workspace_id, 
            OrchestrationRun.state == OrchestrationRunState.EXECUTING
        )
        exec_count = (await self.session.execute(stmt_exec)).scalar() or 0

        # Failed: Phase 3.1
        stmt_fail = select(func.count(Action.id)).where(Action.workspace_id == workspace_id, Action.status == ActionStatus.FAILED)
        failed_count = (await self.session.execute(stmt_fail)).scalar() or 0

        # Completed: Phase 3.1
        stmt_comp = select(func.count(Action.id)).where(Action.workspace_id == workspace_id, Action.status == ActionStatus.COMPLETED)
        completed_count = (await self.session.execute(stmt_comp)).scalar() or 0

        return {
            "ACTIVE_ACTIONS": active_count,
            "BLOCKED_ACTIONS": blocked_count,
            "PENDING_APPROVAL": pending_count,
            "EXECUTING": exec_count,
            "FAILED": failed_count,
            "COMPLETED": completed_count
        }

    async def list_attention_actions(self, workspace_id: UUID, limit: int = 50, offset: int = 0) -> List[OperationalContextDTO]:
        """
        Deterministically returns actions that currently require attention.
        For V1 performance, this first queries actions that are in FAILED state,
        or have active REJECTED approvals, or FAILED orchestration runs.
        """
        # This can be optimized using specific indexed queries. For now, we do a basic union of IDs.
        stmt_failed_actions = select(Action.id).where(Action.workspace_id == workspace_id, Action.status == ActionStatus.FAILED)
        
        stmt_rejected_approvals = select(ApprovalRequest.action_id).where(
            ApprovalRequest.workspace_id == workspace_id, ApprovalRequest.status == ApprovalStatus.REJECTED.value
        )
        
        stmt_failed_runs = select(OrchestrationRun.action_id).where(
            OrchestrationRun.workspace_id == workspace_id, 
            OrchestrationRun.state.in_([OrchestrationRunState.FAILED, OrchestrationRunState.TIMED_OUT])
        )
        
        # Combine the IDs in application memory for V1 (safe for bounded limit)
        ids_set = set()
        for stmt in [stmt_failed_actions, stmt_rejected_approvals, stmt_failed_runs]:
            ids_set.update(row for row in (await self.session.execute(stmt)).scalars().all())
            
        target_ids = list(ids_set)[offset:offset+limit]
        
        results = []
        for a_id in target_ids:
            try:
                ctx = await self.get_operational_context(workspace_id, a_id)
                # Ensure they actually have attention signals before returning
                if ctx.attention_signals:
                    results.append(ctx)
            except ActionNotFoundError:
                continue
                
        return results
