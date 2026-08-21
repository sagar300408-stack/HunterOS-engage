import uuid
from datetime import timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.analytics.models import AnalyticsDailyMetric, AnalyticsMetricType
from app.domain.kpi.engine import KpiIntelligenceEngine
from app.domain.kpi.models import KpiSnapshot, KpiStatus, KpiTrend
from app.domain.kpi.bootstrap import bootstrap_kpis
from app.utils.clock import SystemClock
from tests.domain.events.conftest import pg_session_factory, pg_session

@pytest.mark.asyncio
async def test_b13_kpi_engine_real_persistence(pg_session: AsyncSession, pg_session_factory):
    """
    B13 VERIFICATION:
    Proves that the KPI Intelligence Engine actually calculates KPIs from persisted Analytics data
    and persists the resulting KpiSnapshots. Does NOT use mocks for repositories or database.
    """
    bootstrap_kpis()
    ws_id = uuid.uuid4()
    
    # 1. Prepare raw analytics data (Simulating what would be produced by daily crons)
    now = SystemClock.now()
    # Current period (0 days ago) - meeting conversion rate calculation needs leads & meetings
    # Let's say in the last 30 days: 10 leads, 5 meetings (50% conversion)
    curr_date = (now - timedelta(days=2)).date()
    
    # Previous period (30 days ago) - 20 leads, 4 meetings (20% conversion)
    prev_date = (now - timedelta(days=32)).date()
    
    metrics = [
        AnalyticsDailyMetric(
            workspace_id=ws_id,
            target_type="workspace",
            target_id=ws_id,
            metric_date=curr_date,
            metric_name=AnalyticsMetricType.LEADS_CREATED.value,
            value=10.0
        ),
        AnalyticsDailyMetric(
            workspace_id=ws_id,
            target_type="workspace",
            target_id=ws_id,
            metric_date=curr_date,
            metric_name=AnalyticsMetricType.MEETINGS_SCHEDULED.value,
            value=5.0
        ),
        AnalyticsDailyMetric(
            workspace_id=ws_id,
            target_type="workspace",
            target_id=ws_id,
            metric_date=prev_date,
            metric_name=AnalyticsMetricType.LEADS_CREATED.value,
            value=20.0
        ),
        AnalyticsDailyMetric(
            workspace_id=ws_id,
            target_type="workspace",
            target_id=ws_id,
            metric_date=prev_date,
            metric_name=AnalyticsMetricType.MEETINGS_SCHEDULED.value,
            value=4.0
        ),
    ]
    
    async with pg_session_factory() as s:
        async with s.begin():
            s.add_all(metrics)
            
    # 2. Execute KPI Engine
    async with pg_session_factory() as s:
        engine = KpiIntelligenceEngine(s)
        snapshots = await engine.refresh_kpis(ws_id, "workspace", ws_id)
        
        # 3. Assert memory structures and calculations
        # Find meeting_conversion_rate
        mcr = next((snap for snap in snapshots if snap.kpi_name == "meeting_conversion_rate"), None)
        assert mcr is not None
        
        # Current = 5/10 = 50%
        assert mcr.current_value == 50.0
        # Previous = 4/20 = 20%
        assert mcr.previous_value == 20.0
        # Percentage change = (50 - 20) / 20 * 100 = 150%
        assert mcr.percentage_change == 150.0
        # Target = 25.0, so 50.0 is HEALTHY
        assert mcr.status == KpiStatus.HEALTHY.value
        # Went from 20 to 50 -> UP
        assert mcr.trend == KpiTrend.UP.value
        
        # Ensure it was persisted to the database
        stmt = select(KpiSnapshot).where(KpiSnapshot.id == mcr.id)
        persisted = (await s.execute(stmt)).scalar_one_or_none()
        assert persisted is not None
        assert persisted.current_value == 50.0
