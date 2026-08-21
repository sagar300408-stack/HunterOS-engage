import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.insight.models import InsightSnapshot, InsightCategory, InsightSeverity, InsightLifecycle
from app.domain.recommendation.models import RecommendationSnapshot, RecommendationPriority, RecommendationLifecycle
from app.domain.health.models import HealthSnapshot, HealthStatus
from app.domain.kpi.models import KpiSnapshot
from app.domain.briefing.models import BriefingSnapshot
from app.domain.briefing.engine import ExecutiveBriefingEngine
from app.domain.briefing.bootstrap import bootstrap_briefings
from tests.domain.events.conftest import pg_session_factory, pg_session
from app.utils.clock import SystemClock

@pytest.mark.asyncio
async def test_b15_executive_briefing_real_persistence(pg_session: AsyncSession, pg_session_factory):
    """
    B15 VERIFICATION:
    Proves that the Executive Briefing Engine correctly assembles a briefing 
    by querying real database records (Insights, Recommendations, Health, KPIs)
    and persisting the BriefingSnapshot.
    """
    bootstrap_briefings()
    ws_id = uuid.uuid4()
    now = SystemClock.now()
    
    # 1. Prepare raw database state
    insight = InsightSnapshot(
        workspace_id=ws_id,
        target_type="workspace",
        target_id=ws_id,
        generator_name="test_generator",
        generator_version="1.0",
        title="Critical Sales Drop",
        summary="A 20% drop in sales",
        category=InsightCategory.BUSINESS_RISK.value,
        severity=InsightSeverity.CRITICAL.value,
        impact="HIGH",
        confidence=0.9,
        lifecycle_status=InsightLifecycle.ACTIVE.value,
        trigger_source="manual",
        evidence_graph={}
    )
    
    rec = RecommendationSnapshot(
        workspace_id=ws_id,
        target_type="workspace",
        target_id=ws_id,
        generator_name="test_generator",
        generator_version="1.0",
        title="Fix Sales Pipeline",
        summary="Urgent pipeline intervention",
        category="sales",
        expected_impact="HIGH",
        risk_level="HIGH",
        priority=RecommendationPriority.URGENT.value,
        confidence=0.95,
        lifecycle_status=RecommendationLifecycle.ACTIVE.value,
        trigger_source="manual",
        suggested_actions=[]
    )
    
    health = HealthSnapshot(
        workspace_id=ws_id,
        target_type="workspace",
        target_id=ws_id,
        health_name="customer_engagement_health",
        status=HealthStatus.WARNING.value,
        current_score=60.0,
        trend="down",
        severity="INFO",
        confidence=0.9
    )
    
    kpi = KpiSnapshot(
        workspace_id=ws_id,
        target_type="workspace",
        target_id=ws_id,
        kpi_name="reply_rate",
        category="customer",
        unit="percentage",
        direction="higher_is_better",
        current_value=12.5,
        previous_value=27.5,
        percentage_change=-15.0,
        trend="down",
        status="WARNING",
        confidence=0.8,
        data_source="analytics",
        refresh_strategy="daily"
    )
    
    async with pg_session_factory() as s:
        async with s.begin():
            s.add_all([insight, rec, health, kpi])
            
    # 2. Execute Briefing Engine
    async with pg_session_factory() as s:
        engine = ExecutiveBriefingEngine(s)
        snapshot = await engine.generate_briefing(ws_id, "ceo_daily", "daily")
        
        # 3. Assert briefing assembly
        assert snapshot.template_name == "ceo_daily"
        assert snapshot.period == "daily"
        
        # Verify Critical Risks parsed from Insights
        assert len(snapshot.critical_risks) == 1
        assert snapshot.critical_risks[0]["title"] == "Critical Sales Drop"
        
        # Verify Priority Recommendations
        assert len(snapshot.priority_recommendations) == 1
        assert snapshot.priority_recommendations[0]["title"] == "Fix Sales Pipeline"
        
        # Verify References
        assert str(insight.id) in snapshot.supporting_references
        assert str(rec.id) in snapshot.supporting_references
        assert str(health.id) in snapshot.supporting_references
        assert str(kpi.id) in snapshot.supporting_references
        
        # Verify Confidence Average (0.9 and 0.95)
        assert snapshot.confidence == 0.925
        
        # 4. Verify DB persistence
        stmt = select(BriefingSnapshot).where(BriefingSnapshot.id == snapshot.id)
        persisted = (await s.execute(stmt)).scalar_one_or_none()
        assert persisted is not None
        assert persisted.template_name == "ceo_daily"
