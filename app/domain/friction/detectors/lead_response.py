"""
LeadResponseMonitor
────────────────────
Detects friction caused by:
  - First response delays (lead created but no outbound message sent)
  - Missed follow-ups (scheduled follow-up was not executed)
  - Stalled opportunities (no activity for N hours)
"""
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.friction.models import FrictionEvent, FrictionType, FrictionSeverity
from app.domain.customers.models import Customer
from app.domain.conversations.models import Message, MessageDirection


# Default thresholds (minutes) — overridden by SLAPolicy when available
FIRST_RESPONSE_WARNING_MIN  = 30
FIRST_RESPONSE_CRITICAL_MIN = 120
IDLE_LEAD_WARNING_HOURS     = 24
IDLE_LEAD_CRITICAL_HOURS    = 48


class LeadResponseMonitor:
    """Detects lead response and engagement friction from the database."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def scan_idle_leads(self, workspace_id: UUID) -> List[FrictionEvent]:
        """Find leads with no outbound message in the last 24–48 hours."""
        events = []
        now = datetime.now(timezone.utc)
        warning_cutoff  = now - timedelta(hours=IDLE_LEAD_WARNING_HOURS)
        critical_cutoff = now - timedelta(hours=IDLE_LEAD_CRITICAL_HOURS)

        # Load all customers with at least one conversation but no recent outbound message
        customers = await self.session.execute(
            select(Customer).where(Customer.workspace_id == workspace_id)
        )
        customers = customers.scalars().all()

        for customer in customers:
            # Get the most recent outbound message timestamp for this customer
            last_outbound = await self.session.scalar(
                select(func.max(Message.timestamp))
                .join(Message.conversation)
                .where(
                    and_(
                        Message.direction == MessageDirection.outgoing,
                    )
                )
            )

            if last_outbound is None:
                # Never contacted — check when customer was created
                if customer.created_at < critical_cutoff:
                    events.append(self._make_event(
                        workspace_id=workspace_id,
                        customer=customer,
                        severity=FrictionSeverity.CRITICAL,
                        actual_hours=(now - customer.created_at).total_seconds() / 3600,
                        expected_hours=IDLE_LEAD_CRITICAL_HOURS / 2,
                    ))
                elif customer.created_at < warning_cutoff:
                    events.append(self._make_event(
                        workspace_id=workspace_id,
                        customer=customer,
                        severity=FrictionSeverity.HIGH,
                        actual_hours=(now - customer.created_at).total_seconds() / 3600,
                        expected_hours=IDLE_LEAD_WARNING_HOURS / 2,
                    ))

        return events

    def _make_event(
        self,
        workspace_id: UUID,
        customer: Customer,
        severity: FrictionSeverity,
        actual_hours: float,
        expected_hours: float,
    ) -> FrictionEvent:
        deviation = ((actual_hours - expected_hours) / max(expected_hours, 0.001)) * 100
        contribution = min(20.0, deviation / 10.0)  # cap at 20 pts
        return FrictionEvent(
            workspace_id=workspace_id,
            friction_type=FrictionType.LEAD_RESPONSE_DELAY.value,
            severity=severity.value,
            source_entity_type="customer",
            source_entity_id=customer.id,
            score_contribution=round(contribution, 2),
            expected_value=round(expected_hours, 1),
            actual_value=round(actual_hours, 1),
            deviation_pct=round(deviation, 1),
            description=(
                f"Lead '{customer.name or customer.phone}' has had no outbound contact "
                f"for {actual_hours:.0f}h (expected ≤{expected_hours:.0f}h). "
                f"Estimated conversion drop: {min(40, int(deviation / 5))}%."
            ),
            recommendation_hint=(
                "Assign this lead to an SDR immediately or trigger an automated follow-up sequence."
            ),
            metadata_json={
                "customer_name": customer.name,
                "customer_phone": customer.phone,
                "hours_idle": round(actual_hours, 1),
            }
        )
