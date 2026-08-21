import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.health.models import HealthSnapshot, HealthTrend, HealthStatus, HealthSeverity
from app.domain.kpi.models import KpiSnapshot, KpiStatus, KpiDirection, KpiTrend
from app.domain.insight.models import InsightSnapshot, InsightLifecycle, InsightCategory
from app.domain.insight.engine import InsightEngine
from app.domain.insight.bootstrap import bootstrap_insights
from tests.domain.events.conftest import pg_session_factory, pg_session

@pytest.mark.asyncio
async def test_b14_insight_engine_real_persistence(pg_session: AsyncSession, pg_session_factory):
    """
    B14 VERIFICATION:
    Proves that the Insight Engine queries real Health and KPI snapshots from PostgreSQL,
    generates an evidence graph, and persists an InsightSnapshot.
    """
    bootstrap_insights()
    ws_id = uuid.uuid4()
    
    # 1. Prepare raw health & KPI snapshots
    health_snap = HealthSnapshot(
        workspace_id=ws_id,
        target_type="workspace",
        target_id=ws_id,
        health_name="customer_engagement_health",
        current_score=85.0,
        trend=HealthTrend.UP.value,
        status=HealthStatus.EXCELLENT.value,
        severity=HealthSeverity.INFO.value,
        confidence=0.9
    )
    
    kpi_snap = KpiSnapshot(
        workspace_id=ws_id,
        target_type="workspace",
        target_id=ws_id,
        kpi_name="reply_rate",
        category="customer",
        unit="percentage",
        direction=KpiDirection.HIGHER_IS_BETTER.value,
        current_value=60.0,
        previous_value=50.0,
        percentage_change=20.0,  # > 0 required for EngagementImprovementGenerator
        trend=KpiTrend.UP.value,
        status=KpiStatus.HEALTHY.value,
        target=50.0,
        confidence=0.9,
        data_source="analytics",
        refresh_strategy="daily"
    )
    
    async with pg_session_factory() as s:
        async with s.begin():
            s.add_all([health_snap, kpi_snap])
            
    # 2. Execute Insight Engine
    async with pg_session_factory() as s:
        engine = InsightEngine(s)
        insights = await engine.generate_insights(ws_id, "workspace", ws_id)
        
        # 3. Assert memory structures and calculations
        assert len(insights) >= 1
        
        # Find EngagementImprovementGenerator insight
        insight = next((i for i in insights if i.generator_name == "EngagementImprovementGenerator"), None)
        assert insight is not None
        
        assert insight.category == InsightCategory.PERFORMANCE_IMPROVEMENT.value
        assert insight.lifecycle_status == InsightLifecycle.ACTIVE.value
        
        # Check evidence graph structure
        assert "nodes" in insight.evidence_graph
        assert "edges" in insight.evidence_graph
        
        nodes = insight.evidence_graph["nodes"]
        node_types = [n.get("node_type") for n in nodes]
        assert "HEALTH" in node_types
        assert "KPI" in node_types
        
        # 4. Verify DB persistence
        stmt = select(InsightSnapshot).where(InsightSnapshot.id == insight.id)
        persisted = (await s.execute(stmt)).scalar_one_or_none()
        assert persisted is not None
        assert persisted.title == insight.title
