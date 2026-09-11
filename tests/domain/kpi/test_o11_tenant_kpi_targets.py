import pytest
import uuid

from app.domain.kpi.engine import KpiIntelligenceEngine
from app.domain.impact.models import BusinessTargets
from app.domain.analytics.models import AnalyticsDailyMetric, AnalyticsMetricType
from app.domain.customers.models import Customer
from app.domain.conversations.models import Conversation
from datetime import datetime, timezone, timedelta
from app.utils.clock import SystemClock
from tests.domain.events.conftest import pg_session_factory, pg_engine, pg_session

from app.domain.kpi.bootstrap import bootstrap_kpis

@pytest.mark.asyncio
async def test_o11_tenant_configurable_kpi_targets(pg_session_factory):
    # Ensure KPIs are registered
    bootstrap_kpis()
    workspace_id = uuid.uuid4()
    target_id = uuid.uuid4()
    
    async with pg_session_factory() as session:
        async with session.begin():
            # Add custom business target for meeting_conversion_rate
            custom_target = BusinessTargets(
                workspace_id=workspace_id,
                kpi_name="meeting_conversion_rate",
                target_value=45.0
            )
            session.add(custom_target)
            
            # Add some analytics data so the KPI doesn't just error out or return 0
            end_date = SystemClock.now().date()
            m1 = AnalyticsDailyMetric(
                workspace_id=workspace_id,
                target_type="workspace",
                target_id=target_id,
                metric_name=AnalyticsMetricType.LEADS_CREATED.value,
                metric_date=end_date,
                value=100
            )
            m2 = AnalyticsDailyMetric(
                workspace_id=workspace_id,
                target_type="workspace",
                target_id=target_id,
                metric_name=AnalyticsMetricType.MEETINGS_SCHEDULED.value,
                metric_date=end_date,
                value=25
            )
            session.add_all([m1, m2])
            
    async with pg_session_factory() as session:
        engine = KpiIntelligenceEngine(session)
        snapshots = await engine.refresh_kpis(workspace_id, "workspace", target_id)
        
        # Check meeting_conversion_rate target was overridden
        meeting_kpi = next((s for s in snapshots if s.kpi_name == "meeting_conversion_rate"), None)
        assert meeting_kpi is not None
        assert meeting_kpi.target == 45.0 # Should be overridden from 25.0
        
        # Check reply_rate which didn't have an override
        reply_kpi = next((s for s in snapshots if s.kpi_name == "reply_rate"), None)
        assert reply_kpi is not None
        assert reply_kpi.target == 50.0 # Default value
