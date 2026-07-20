from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.friction.models import (
    FrictionEvent, FrictionResolution,
    FrictionScoreSnapshot, SLAPolicy,
    WorkflowStageLatency, WorkflowStageStatus,
)


class FrictionRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Friction Events ───────────────────────────────────────────────────────

    async def save_friction_event(self, event: FrictionEvent) -> FrictionEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_friction_events(
        self,
        workspace_id: UUID,
        friction_type: Optional[str] = None,
        severity: Optional[str] = None,
        resolution_status: Optional[str] = None,
        limit: int = 50,
    ) -> List[FrictionEvent]:
        q = select(FrictionEvent).where(FrictionEvent.workspace_id == workspace_id)
        if friction_type:
            q = q.where(FrictionEvent.friction_type == friction_type)
        if severity:
            q = q.where(FrictionEvent.severity == severity)
        if resolution_status:
            q = q.where(FrictionEvent.resolution_status == resolution_status)
        q = q.order_by(desc(FrictionEvent.detected_at)).limit(limit)
        result = await self.session.execute(q)
        return result.scalars().all()

    async def get_open_friction_events(self, workspace_id: UUID) -> List[FrictionEvent]:
        result = await self.session.execute(
            select(FrictionEvent).where(
                and_(
                    FrictionEvent.workspace_id == workspace_id,
                    FrictionEvent.resolution_status == FrictionResolution.OPEN.value
                )
            ).order_by(desc(FrictionEvent.score_contribution))
        )
        return result.scalars().all()

    async def count_open_events(self, workspace_id: UUID) -> int:
        return await self.session.scalar(
            select(func.count(FrictionEvent.id)).where(
                and_(
                    FrictionEvent.workspace_id == workspace_id,
                    FrictionEvent.resolution_status == FrictionResolution.OPEN.value
                )
            )
        ) or 0

    async def count_critical_events(self, workspace_id: UUID) -> int:
        return await self.session.scalar(
            select(func.count(FrictionEvent.id)).where(
                and_(
                    FrictionEvent.workspace_id == workspace_id,
                    FrictionEvent.resolution_status == FrictionResolution.OPEN.value,
                    FrictionEvent.severity == "CRITICAL"
                )
            )
        ) or 0

    async def get_open_events_by_type(self, workspace_id: UUID) -> dict:
        """Returns {friction_type: count} for all open events."""
        result = await self.session.execute(
            select(FrictionEvent.friction_type, func.count(FrictionEvent.id).label("cnt"))
            .where(
                and_(
                    FrictionEvent.workspace_id == workspace_id,
                    FrictionEvent.resolution_status == FrictionResolution.OPEN.value
                )
            )
            .group_by(FrictionEvent.friction_type)
        )
        return {row.friction_type: row.cnt for row in result.all()}

    # ── Score Snapshots ───────────────────────────────────────────────────────

    async def save_score_snapshot(self, snapshot: FrictionScoreSnapshot) -> FrictionScoreSnapshot:
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_latest_score(self, workspace_id: UUID) -> Optional[FrictionScoreSnapshot]:
        result = await self.session.execute(
            select(FrictionScoreSnapshot)
            .where(FrictionScoreSnapshot.workspace_id == workspace_id)
            .order_by(desc(FrictionScoreSnapshot.calculated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_score_history(self, workspace_id: UUID, days: int = 30) -> List[FrictionScoreSnapshot]:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(FrictionScoreSnapshot)
            .where(
                and_(
                    FrictionScoreSnapshot.workspace_id == workspace_id,
                    FrictionScoreSnapshot.calculated_at >= cutoff
                )
            )
            .order_by(FrictionScoreSnapshot.calculated_at)
        )
        return result.scalars().all()

    # ── SLA Policies ──────────────────────────────────────────────────────────

    async def save_sla_policy(self, policy: SLAPolicy) -> SLAPolicy:
        self.session.add(policy)
        await self.session.flush()
        return policy

    async def get_sla_policies(self, workspace_id: UUID, active_only: bool = True) -> List[SLAPolicy]:
        q = select(SLAPolicy).where(SLAPolicy.workspace_id == workspace_id)
        if active_only:
            q = q.where(SLAPolicy.is_active == True)
        result = await self.session.execute(q)
        return result.scalars().all()

    # ── Workflow Latency ──────────────────────────────────────────────────────

    async def upsert_workflow_latency(
        self,
        workspace_id: UUID,
        stage_name: str,
        new_duration_hours: float,
        expected_duration_hours: float,
    ) -> WorkflowStageLatency:
        result = await self.session.execute(
            select(WorkflowStageLatency).where(
                and_(
                    WorkflowStageLatency.workspace_id == workspace_id,
                    WorkflowStageLatency.stage_name == stage_name,
                )
            )
        )
        record = result.scalar_one_or_none()

        if not record:
            record = WorkflowStageLatency(
                workspace_id=workspace_id,
                stage_name=stage_name,
                expected_duration_hours=expected_duration_hours,
                actual_avg_hours=new_duration_hours,
                sample_count=1,
            )
        else:
            # Rolling average update
            total = record.actual_avg_hours * record.sample_count + new_duration_hours
            record.sample_count += 1
            record.actual_avg_hours = total / record.sample_count
            record.expected_duration_hours = expected_duration_hours

        # Determine status
        ratio = record.actual_avg_hours / max(record.expected_duration_hours, 0.001)
        if ratio >= 3.0:
            record.status = WorkflowStageStatus.CRITICAL.value
        elif ratio >= 2.0:
            record.status = WorkflowStageStatus.BOTTLENECK.value
        elif ratio >= 1.3:
            record.status = WorkflowStageStatus.WARNING.value
        else:
            record.status = WorkflowStageStatus.NORMAL.value

        self.session.add(record)
        await self.session.flush()
        return record

    async def get_workflow_latency(self, workspace_id: UUID) -> List[WorkflowStageLatency]:
        result = await self.session.execute(
            select(WorkflowStageLatency)
            .where(WorkflowStageLatency.workspace_id == workspace_id)
            .order_by(desc(WorkflowStageLatency.actual_avg_hours))
        )
        return result.scalars().all()

    async def get_bottleneck_stages(self, workspace_id: UUID) -> List[WorkflowStageLatency]:
        result = await self.session.execute(
            select(WorkflowStageLatency).where(
                and_(
                    WorkflowStageLatency.workspace_id == workspace_id,
                    WorkflowStageLatency.status.in_([
                        WorkflowStageStatus.BOTTLENECK.value,
                        WorkflowStageStatus.CRITICAL.value
                    ])
                )
            ).order_by(desc(WorkflowStageLatency.actual_avg_hours))
        )
        return result.scalars().all()
