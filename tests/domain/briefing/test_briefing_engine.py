import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.domain.briefing.engine import ExecutiveBriefingEngine
from app.domain.briefing.templates.standard_templates import CEODailyBriefing
from app.domain.insight.models import InsightSnapshot, InsightCategory, InsightSeverity
from app.domain.recommendation.models import RecommendationSnapshot, RecommendationPriority
from app.domain.health.models import HealthSnapshot, HealthStatus
from app.domain.kpi.models import KpiSnapshot

# SQLAlchemy mapping requirements
from app.domain.briefing import models as briefing_models
from app.domain.recommendation import models as rec_models
from app.domain.insight import models as insight_models
from app.domain.health import models as health_models
from app.domain.kpi import models as kpi_models
from app.domain.conversations import models as conv_models
from app.domain.customers import models as cust_models
from app.domain.scheduling import models as sched_models
from app.domain.followup import models as followup_models
from app.domain.intent import models as intent_models
from app.domain.memory import models as memory_models

@pytest.mark.asyncio
async def test_executive_briefing_engine_ceo_template():
    mock_session = AsyncMock()
    workspace_id = uuid.uuid4()
    
    # Mock Registry
    mock_registry = MagicMock()
    mock_registry.get_template.return_value = CEODailyBriefing()
    
    # Mock Data
    mock_insight = InsightSnapshot(
        id=uuid.uuid4(),
        title="Critical Sales Drop",
        summary="A 20% drop in sales",
        category=InsightCategory.BUSINESS_RISK.value,
        severity=InsightSeverity.CRITICAL.value,
        confidence=0.9
    )
    
    mock_rec = RecommendationSnapshot(
        id=uuid.uuid4(),
        title="Fix Sales Pipeline",
        summary="Urgent pipeline intervention",
        priority=RecommendationPriority.URGENT.value,
        confidence=0.95,
        suggested_actions=[]
    )
    
    mock_health = HealthSnapshot(
        id=uuid.uuid4(),
        health_name="customer_engagement_health",
        status=HealthStatus.WARNING.value,
        current_score=60.0,
        trend="down"
    )
    
    mock_kpi = KpiSnapshot(
        id=uuid.uuid4(),
        kpi_name="reply_rate",
        current_value=12.5,
        percentage_change=-15.0
    )
    
    engine = ExecutiveBriefingEngine(mock_session)
    engine.composer.insight_repo.get_latest_insights = AsyncMock(return_value=[mock_insight])
    engine.composer.recommendation_repo.get_latest_recommendations = AsyncMock(return_value=[mock_rec])
    engine.composer.health_repo.get_latest_health = AsyncMock(return_value=[mock_health])
    engine.composer.kpi_repo.get_latest_kpis = AsyncMock(return_value=[mock_kpi])
    
    async def mock_save(briefing):
        return briefing
    engine.briefing_repo.save_briefing = AsyncMock(side_effect=mock_save)
    
    with patch("app.domain.briefing.engine.briefing_registry", mock_registry):
        snapshot = await engine.generate_briefing(workspace_id, "ceo_daily", "daily")
        
        # Verify Snapshot
        assert snapshot.template_name == "ceo_daily"
        assert snapshot.period == "daily"
        
        # Verify Critical Risks parsed from Insights
        assert len(snapshot.critical_risks) == 1
        assert snapshot.critical_risks[0]["title"] == "Critical Sales Drop"
        
        # Verify Priority Recommendations
        assert len(snapshot.priority_recommendations) == 1
        assert snapshot.priority_recommendations[0]["title"] == "Fix Sales Pipeline"
        
        # Verify References
        assert str(mock_insight.id) in snapshot.supporting_references
        assert str(mock_rec.id) in snapshot.supporting_references
        assert str(mock_health.id) in snapshot.supporting_references
        assert str(mock_kpi.id) in snapshot.supporting_references
        
        # Verify Confidence Average (0.9 and 0.95)
        assert snapshot.confidence == 0.925
