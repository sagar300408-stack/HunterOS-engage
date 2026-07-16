from datetime import date
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics.models import AnalyticsDailyMetric, AnalyticsMetricType


class AnalyticsRepository:
    """
    Manages persistence and retrieval of Analytics metrics.
    """

    async def increment_metric(
        self, 
        session: AsyncSession, 
        workspace_id: UUID, 
        target_type: str, 
        target_id: UUID, 
        metric_date: date, 
        metric_name: AnalyticsMetricType,
        amount: int = 1
    ) -> AnalyticsDailyMetric:
        """
        Increments a metric bucket. Creates it if it doesn't exist.
        Since we might use sqlite, we avoid ON CONFLICT and use a simple select-then-insert/update.
        In a high concurrency Postgres environment, we'd use insert().on_conflict_do_update().
        """
        stmt = select(AnalyticsDailyMetric).where(
            AnalyticsDailyMetric.workspace_id == workspace_id,
            AnalyticsDailyMetric.target_type == target_type,
            AnalyticsDailyMetric.target_id == target_id,
            AnalyticsDailyMetric.metric_date == metric_date,
            AnalyticsDailyMetric.metric_name == metric_name
        )
        result = await session.execute(stmt)
        metric = result.scalars().first()

        if metric:
            metric.value += amount
        else:
            metric = AnalyticsDailyMetric(
                workspace_id=workspace_id,
                target_type=target_type,
                target_id=target_id,
                metric_date=metric_date,
                metric_name=metric_name,
                value=amount
            )
            session.add(metric)
        
        await session.flush()
        return metric

    async def get_metrics(
        self, 
        session: AsyncSession, 
        workspace_id: UUID, 
        target_type: str = None, 
        target_id: UUID = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[AnalyticsDailyMetric]:
        """
        Retrieves analytics metrics based on filters.
        """
        stmt = select(AnalyticsDailyMetric).where(AnalyticsDailyMetric.workspace_id == workspace_id)
        
        if target_type:
            stmt = stmt.where(AnalyticsDailyMetric.target_type == target_type)
        if target_id:
            stmt = stmt.where(AnalyticsDailyMetric.target_id == target_id)
        if start_date:
            stmt = stmt.where(AnalyticsDailyMetric.metric_date >= start_date)
        if end_date:
            stmt = stmt.where(AnalyticsDailyMetric.metric_date <= end_date)
            
        stmt = stmt.order_by(AnalyticsDailyMetric.metric_date.desc())
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
