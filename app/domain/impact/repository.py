import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.domain.impact.models import (
    FinancialConfig,
    BusinessTargets,
    BaselineMetrics,
    ImpactEvent,
    ValueAttribution,
    ExecutiveImpactReport
)

class ImpactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_financial_config(self, workspace_id: uuid.UUID) -> FinancialConfig:
        result = await self.session.execute(
            select(FinancialConfig).where(FinancialConfig.workspace_id == workspace_id)
        )
        config = result.scalars().first()
        if not config:
            # Default config if none exists
            config = FinancialConfig(workspace_id=workspace_id)
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)
        return config

    async def get_business_targets(self, workspace_id: uuid.UUID) -> List[BusinessTargets]:
        result = await self.session.execute(
            select(BusinessTargets).where(BusinessTargets.workspace_id == workspace_id)
        )
        return result.scalars().all()

    async def get_baseline_metrics(self, workspace_id: uuid.UUID) -> List[BaselineMetrics]:
        result = await self.session.execute(
            select(BaselineMetrics).where(BaselineMetrics.workspace_id == workspace_id)
        )
        return result.scalars().all()

    async def save_impact_event(self, event: ImpactEvent) -> ImpactEvent:
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def save_attribution(self, attribution: ValueAttribution) -> ValueAttribution:
        self.session.add(attribution)
        await self.session.commit()
        await self.session.refresh(attribution)
        return attribution

    async def get_attributions_for_period(self, workspace_id: uuid.UUID, start_date, end_date) -> List[ValueAttribution]:
        result = await self.session.execute(
            select(ValueAttribution)
            .options(selectinload(ValueAttribution.evidence_traces))
            .where(
                ValueAttribution.workspace_id == workspace_id,
                ValueAttribution.created_at >= start_date,
                ValueAttribution.created_at <= end_date
            )
        )
        return result.scalars().all()

    async def save_executive_report(self, report: ExecutiveImpactReport) -> ExecutiveImpactReport:
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report
        
    async def list_reports(self, workspace_id: uuid.UUID) -> List[ExecutiveImpactReport]:
        result = await self.session.execute(
            select(ExecutiveImpactReport)
            .where(ExecutiveImpactReport.workspace_id == workspace_id)
            .order_by(ExecutiveImpactReport.created_at.desc())
        )
        return result.scalars().all()
