"""
ApprovalDelayDetector
──────────────────────
Detects approval requests that have been pending beyond configured thresholds.
Recommends escalation paths when the approver is identified as offline/unresponsive.
"""
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.friction.models import FrictionEvent, FrictionType, FrictionSeverity


# Default thresholds — can be driven by SLAPolicy in future
APPROVAL_WARNING_HOURS  = 4
APPROVAL_CRITICAL_HOURS = 12


class ApprovalDelayDetector:
    """Detects pending approvals that have exceeded acceptable wait times."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def scan_delayed_approvals(self, workspace_id: UUID) -> List[FrictionEvent]:
        """Scan the approval domain for stalled requests."""
        try:
            from app.domain.approval.models import ApprovalRequest, ApprovalStatus
        except ImportError:
            return []

        events = []
        now = datetime.now(timezone.utc)
        warning_cutoff  = now - timedelta(hours=APPROVAL_WARNING_HOURS)
        critical_cutoff = now - timedelta(hours=APPROVAL_CRITICAL_HOURS)

        result = await self.session.execute(
            select(ApprovalRequest).where(
                and_(
                    ApprovalRequest.workspace_id == workspace_id,
                    ApprovalRequest.status == ApprovalStatus.PENDING.value,
                    ApprovalRequest.created_at < warning_cutoff,
                )
            )
        )
        pending = result.scalars().all()

        for req in pending:
            wait_hours = (now - req.created_at).total_seconds() / 3600

            if req.created_at < critical_cutoff:
                severity    = FrictionSeverity.CRITICAL
                contribution = 12.0
                hint = (
                    "Escalate immediately to the next approver. "
                    "Consider delegating approvals below a threshold to a secondary approver."
                )
            else:
                severity    = FrictionSeverity.HIGH
                contribution = 6.0
                hint = (
                    "Send a reminder to the approver. "
                    "If no response within 2 hours, escalate automatically."
                )

            events.append(FrictionEvent(
                workspace_id=workspace_id,
                friction_type=FrictionType.APPROVAL_DELAY.value,
                severity=severity.value,
                source_entity_type="approval",
                source_entity_id=req.id,
                score_contribution=contribution,
                expected_value=float(APPROVAL_WARNING_HOURS),
                actual_value=round(wait_hours, 2),
                deviation_pct=round(((wait_hours - APPROVAL_WARNING_HOURS) /
                                     max(APPROVAL_WARNING_HOURS, 0.01)) * 100, 1),
                description=(
                    f"Approval request '{getattr(req, 'action_type', 'UNKNOWN')}' "
                    f"has been pending for {wait_hours:.1f}h "
                    f"(threshold: {APPROVAL_WARNING_HOURS}h). "
                    f"Blocking downstream operations."
                ),
                recommendation_hint=hint,
                metadata_json={
                    "approval_id": str(req.id),
                    "wait_hours": round(wait_hours, 2),
                    "action_type": getattr(req, "action_type", "UNKNOWN"),
                }
            ))

        return events
