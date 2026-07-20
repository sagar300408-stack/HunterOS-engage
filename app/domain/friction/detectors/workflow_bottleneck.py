"""
WorkflowBottleneckDetector
───────────────────────────
Tracks average time leads spend at each pipeline stage.
Compares against expected baselines and flags critical bottlenecks.
"""
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.friction.models import FrictionEvent, FrictionType, FrictionSeverity
from app.domain.friction.repository import FrictionRepository
from app.domain.customers.models import Customer


# Configurable expected stage durations (hours) — workspace-level overrides planned in M2
STAGE_BASELINES: Dict[str, float] = {
    "Research":           48.0,
    "Comparing Options":  72.0,
    "Ready to Schedule":  24.0,
    "Negotiation":        96.0,
    "Purchase Ready":     24.0,
}


class WorkflowBottleneckDetector:
    """Detects stalled pipeline stages and generates friction events."""

    def __init__(self, session: AsyncSession, repo: FrictionRepository):
        self.session = session
        self.repo    = repo

    async def scan_workflow_bottlenecks(self, workspace_id: UUID) -> List[FrictionEvent]:
        """
        Compute rolling average time-in-stage for each buying_stage.
        Compare against STAGE_BASELINES and generate FrictionEvents for bottlenecks.
        """
        events = []
        now = datetime.now(timezone.utc)

        for stage, expected_hours in STAGE_BASELINES.items():
            # Find all customers currently in this stage
            result = await self.session.execute(
                select(Customer).where(
                    and_(
                        Customer.workspace_id == workspace_id,
                        Customer.buying_stage == stage,
                    )
                )
            )
            customers = result.scalars().all()
            if not customers:
                continue

            # Compute average hours spent in this stage (proxy: time since last_interaction or created_at)
            durations = []
            for c in customers:
                ref = c.last_interaction or c.created_at
                if ref:
                    hours = (now - ref).total_seconds() / 3600
                    durations.append(hours)

            if not durations:
                continue

            avg_hours = sum(durations) / len(durations)

            # Update rolling average in DB
            await self.repo.upsert_workflow_latency(
                workspace_id=workspace_id,
                stage_name=stage,
                new_duration_hours=avg_hours,
                expected_duration_hours=expected_hours,
            )

            # Generate friction event if bottleneck detected
            ratio = avg_hours / max(expected_hours, 0.001)
            if ratio < 1.3:
                continue  # within acceptable range

            if ratio >= 3.0:
                severity    = FrictionSeverity.CRITICAL
                contribution = 15.0
            elif ratio >= 2.0:
                severity    = FrictionSeverity.HIGH
                contribution = 8.0
            else:
                severity    = FrictionSeverity.MEDIUM
                contribution = 4.0

            deviation = (ratio - 1.0) * 100

            events.append(FrictionEvent(
                workspace_id=workspace_id,
                friction_type=FrictionType.WORKFLOW_STALL.value,
                severity=severity.value,
                source_entity_type="pipeline_stage",
                source_entity_id=None,
                score_contribution=contribution,
                expected_value=round(expected_hours, 1),
                actual_value=round(avg_hours, 1),
                deviation_pct=round(deviation, 1),
                description=(
                    f"Pipeline stage '{stage}' is running {ratio:.1f}× slower than expected. "
                    f"Average time: {avg_hours:.1f}h vs expected {expected_hours:.1f}h. "
                    f"{len(customers)} leads currently stalled."
                ),
                recommendation_hint=(
                    f"Review leads in '{stage}' stage. Consider auto-escalating leads "
                    f"that exceed {expected_hours * 1.5:.0f}h with no activity."
                ),
                metadata_json={
                    "stage": stage,
                    "expected_hours": expected_hours,
                    "actual_avg_hours": round(avg_hours, 1),
                    "ratio": round(ratio, 2),
                    "customer_count": len(customers),
                }
            ))

        return events
