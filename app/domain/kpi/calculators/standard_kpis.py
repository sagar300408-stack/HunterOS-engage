from datetime import datetime, timedelta
from typing import Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.domain.analytics.models import AnalyticsDailyMetric, AnalyticsMetricType
from app.domain.analytics.repository import AnalyticsRepository
from app.domain.kpi.calculators.base import BaseKpiCalculator
from app.domain.kpi.models import KpiCategory, KpiDirection, KpiUnit
from app.domain.kpi.schemas import KpiCalculationResult, KpiDefinition
from app.utils.clock import SystemClock


class MeetingConversionRateCalculator(BaseKpiCalculator):
    @property
    def definition(self) -> KpiDefinition:
        return KpiDefinition(
            name="meeting_conversion_rate",
            category=KpiCategory.SALES,
            description="Percentage of new leads that successfully scheduled a meeting in the last 30 days.",
            unit=KpiUnit.PERCENTAGE,
            direction=KpiDirection.HIGHER_IS_BETTER,
            target=25.0,  # Example target 25%
            warning_threshold=15.0,
            critical_threshold=10.0,
            data_source="analytics_projection",
            refresh_strategy="daily"
        )

    async def _get_totals(self, session: AsyncSession, repo: AnalyticsRepository, target_type: str, target_id: UUID, days_ago: int) -> Tuple[int, int]:
        end_date = SystemClock.now().date() - timedelta(days=days_ago)
        start_date = end_date - timedelta(days=30)
        
        # Calculate for [start_date, end_date]
        stmt = select(AnalyticsDailyMetric.metric_name, func.sum(AnalyticsDailyMetric.value)).where(
            AnalyticsDailyMetric.target_type == target_type,
            AnalyticsDailyMetric.target_id == target_id,
            AnalyticsDailyMetric.metric_date >= start_date,
            AnalyticsDailyMetric.metric_date <= end_date,
            AnalyticsDailyMetric.metric_name.in_([
                AnalyticsMetricType.LEADS_CREATED.value, 
                AnalyticsMetricType.MEETINGS_SCHEDULED.value
            ])
        ).group_by(AnalyticsDailyMetric.metric_name)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        leads = 0
        meetings = 0
        for name, total in rows:
            if name == AnalyticsMetricType.LEADS_CREATED.value:
                leads = total or 0
            elif name == AnalyticsMetricType.MEETINGS_SCHEDULED.value:
                meetings = total or 0
                
        return leads, meetings

    async def calculate(
        self, 
        session: AsyncSession, 
        analytics_repo: AnalyticsRepository, 
        target_type: str, 
        target_id: UUID
    ) -> KpiCalculationResult:
        
        # Current period (last 30 days)
        curr_leads, curr_meetings = await self._get_totals(session, analytics_repo, target_type, target_id, days_ago=0)
        
        # Previous period (30 days before that)
        prev_leads, prev_meetings = await self._get_totals(session, analytics_repo, target_type, target_id, days_ago=30)
        
        curr_val = (curr_meetings / curr_leads * 100.0) if curr_leads > 0 else 0.0
        prev_val = (prev_meetings / prev_leads * 100.0) if prev_leads > 0 else 0.0
        
        perc_change = None
        if prev_val > 0:
            perc_change = ((curr_val - prev_val) / prev_val) * 100.0
            
        return KpiCalculationResult(
            current_value=round(curr_val, 2),
            previous_value=round(prev_val, 2),
            percentage_change=round(perc_change, 2) if perc_change is not None else None,
            confidence=1.0 if curr_leads >= 10 else 0.5  # Lower confidence if small sample size
        )


class ReplyRateCalculator(BaseKpiCalculator):
    @property
    def definition(self) -> KpiDefinition:
        return KpiDefinition(
            name="reply_rate",
            category=KpiCategory.CUSTOMER,
            description="Percentage of conversations where the customer replied in the last 30 days.",
            unit=KpiUnit.PERCENTAGE,
            direction=KpiDirection.HIGHER_IS_BETTER,
            target=50.0,
            warning_threshold=30.0,
            critical_threshold=20.0,
            data_source="analytics_projection",
            refresh_strategy="daily"
        )

    async def _get_totals(self, session: AsyncSession, repo: AnalyticsRepository, target_type: str, target_id: UUID, days_ago: int) -> Tuple[int, int]:
        end_date = SystemClock.now().date() - timedelta(days=days_ago)
        start_date = end_date - timedelta(days=30)
        
        stmt = select(AnalyticsDailyMetric.metric_name, func.sum(AnalyticsDailyMetric.value)).where(
            AnalyticsDailyMetric.target_type == target_type,
            AnalyticsDailyMetric.target_id == target_id,
            AnalyticsDailyMetric.metric_date >= start_date,
            AnalyticsDailyMetric.metric_date <= end_date,
            AnalyticsDailyMetric.metric_name.in_([
                AnalyticsMetricType.CONVERSATIONS_STARTED.value, 
                AnalyticsMetricType.CUSTOMER_REPLIES.value
            ])
        ).group_by(AnalyticsDailyMetric.metric_name)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        started = 0
        replies = 0
        for name, total in rows:
            if name == AnalyticsMetricType.CONVERSATIONS_STARTED.value:
                started = total or 0
            elif name == AnalyticsMetricType.CUSTOMER_REPLIES.value:
                replies = total or 0
                
        return started, replies

    async def calculate(
        self, 
        session: AsyncSession, 
        analytics_repo: AnalyticsRepository, 
        target_type: str, 
        target_id: UUID
    ) -> KpiCalculationResult:
        
        curr_started, curr_replies = await self._get_totals(session, analytics_repo, target_type, target_id, days_ago=0)
        prev_started, prev_replies = await self._get_totals(session, analytics_repo, target_type, target_id, days_ago=30)
        
        # We cap at 100% in case of multiple replies per conversation, or define it differently.
        # But for simplicity, we just do replies/started
        curr_val = min((curr_replies / curr_started * 100.0), 100.0) if curr_started > 0 else 0.0
        prev_val = min((prev_replies / prev_started * 100.0), 100.0) if prev_started > 0 else 0.0
        
        perc_change = None
        if prev_val > 0:
            perc_change = ((curr_val - prev_val) / prev_val) * 100.0
            
        return KpiCalculationResult(
            current_value=round(curr_val, 2),
            previous_value=round(prev_val, 2),
            percentage_change=round(perc_change, 2) if perc_change is not None else None,
            confidence=1.0 if curr_started >= 10 else 0.5
        )
