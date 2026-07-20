"""
SLAMonitoringEngine
────────────────────
Evaluates operational entities against configured SLAPolicy records.
Generates FrictionEvents for WARNING and CRITICAL SLA breaches.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.friction.models import FrictionEvent, FrictionType, FrictionSeverity, SLAPolicy
from app.domain.customers.models import Customer
from app.domain.conversations.models import Message, MessageDirection


class SLAMonitoringEngine:
    """Evaluates SLA compliance based on workspace-configured policies."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def scan_sla_violations(
        self, workspace_id: UUID, policies: List[SLAPolicy]
    ) -> List[FrictionEvent]:
        """Run all active SLA policies and collect violations."""
        events = []
        for policy in policies:
            violations = await self._evaluate_policy(workspace_id, policy)
            events.extend(violations)
        return events

    async def _evaluate_policy(
        self, workspace_id: UUID, policy: SLAPolicy
    ) -> List[FrictionEvent]:
        """Dispatch to the correct evaluation method based on event_trigger."""
        trigger = policy.event_trigger

        if trigger == "lead.created":
            return await self._eval_lead_first_contact(workspace_id, policy)
        elif trigger == "followup.missed":
            return await self._eval_missed_followups(workspace_id, policy)
        else:
            return []

    async def _eval_lead_first_contact(
        self, workspace_id: UUID, policy: SLAPolicy
    ) -> List[FrictionEvent]:
        """Check leads without any outbound contact since creation."""
        events = []
        now = datetime.now(timezone.utc)
        warning_cutoff  = now - timedelta(minutes=policy.warning_threshold_minutes)
        critical_cutoff = now - timedelta(minutes=policy.critical_threshold_minutes)

        customers = await self.session.execute(
            select(Customer).where(Customer.workspace_id == workspace_id)
        )
        customers = customers.scalars().all()

        for cust in customers:
            if not cust.created_at:
                continue
            age_min = (now - cust.created_at).total_seconds() / 60

            # Check if any outbound message has been sent (simple proxy for "contacted")
            outbound_count = await self.session.scalar(
                select(func.count(Message.id))
                .join(Message.conversation)
                .where(Message.direction == MessageDirection.outbound)
            ) or 0

            if outbound_count > 0:
                continue  # contacted — no SLA breach

            if cust.created_at < critical_cutoff:
                severity = FrictionSeverity.CRITICAL
                contribution = 10.0
            elif cust.created_at < warning_cutoff:
                severity = FrictionSeverity.MEDIUM
                contribution = 4.0
            else:
                continue  # still within SLA

            events.append(FrictionEvent(
                workspace_id=workspace_id,
                friction_type=FrictionType.SLA_VIOLATION.value,
                severity=severity.value,
                source_entity_type="customer",
                source_entity_id=cust.id,
                score_contribution=contribution,
                expected_value=float(policy.warning_threshold_minutes),
                actual_value=round(age_min, 1),
                deviation_pct=round(((age_min - policy.warning_threshold_minutes) /
                                     max(policy.warning_threshold_minutes, 1)) * 100, 1),
                description=(
                    f"SLA '{policy.policy_name}' breached: lead '{cust.name or cust.phone}' "
                    f"uncontacted for {age_min:.0f} min (SLA: {policy.warning_threshold_minutes} min)."
                ),
                recommendation_hint=(
                    f"Contact this lead immediately to restore SLA compliance. "
                    f"Consider enabling automated WhatsApp outreach for new leads."
                ),
                metadata_json={
                    "policy_name": policy.policy_name,
                    "sla_warning_min": policy.warning_threshold_minutes,
                    "sla_critical_min": policy.critical_threshold_minutes,
                    "actual_minutes": round(age_min, 1),
                }
            ))

        return events

    async def _eval_missed_followups(
        self, workspace_id: UUID, policy: SLAPolicy
    ) -> List[FrictionEvent]:
        """Check for follow-ups that passed their scheduled time without execution."""
        from app.domain.followup.models import FollowUpQueue
        events = []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=policy.critical_threshold_minutes)

        result = await self.session.execute(
            select(FollowUpQueue).where(
                and_(
                    FollowUpQueue.workspace_id == workspace_id,
                    FollowUpQueue.status == "scheduled",
                    FollowUpQueue.scheduled_for < cutoff,
                    FollowUpQueue.human_paused == False,
                )
            )
        )
        overdue = result.scalars().all()

        for fq in overdue:
            overdue_min = (now - fq.scheduled_for).total_seconds() / 60
            events.append(FrictionEvent(
                workspace_id=workspace_id,
                friction_type=FrictionType.MISSED_FOLLOWUP.value,
                severity=FrictionSeverity.HIGH.value,
                source_entity_type="followup",
                source_entity_id=fq.id,
                score_contribution=5.0,
                expected_value=0.0,
                actual_value=round(overdue_min, 1),
                deviation_pct=100.0,
                description=(
                    f"Follow-up was scheduled but not sent. Overdue by {overdue_min:.0f} minutes."
                ),
                recommendation_hint="Check follow-up engine health and retry failed messages.",
                metadata_json={"followup_id": str(fq.id), "overdue_minutes": round(overdue_min, 1)}
            ))

        return events
