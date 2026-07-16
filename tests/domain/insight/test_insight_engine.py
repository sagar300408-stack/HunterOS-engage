import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.domain.insight.engine import InsightEngine
from app.domain.insight.generators.standard_insights import EngagementImprovementGenerator
from app.domain.insight.models import InsightLifecycle, InsightCategory
from app.domain.health.models import HealthSnapshot, HealthTrend, HealthStatus, HealthSeverity
from app.domain.kpi.models import KpiSnapshot, KpiStatus

# SQLAlchemy mapping requirements
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
async def test_insight_engine_generates_and_supersedes():
    mock_session = AsyncMock()
    workspace_id = uuid.uuid4()
    
    mock_registry = MagicMock()
    mock_registry.get_all_generators.return_value = [EngagementImprovementGenerator()]
    
    # Mock Health 
    mock_health = HealthSnapshot(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        target_type="workspace",
        target_id=workspace_id,
        health_name="customer_engagement_health",
        current_score=55.0,
        trend=HealthTrend.UP.value,
        status=HealthStatus.EXCELLENT.value,
        severity=HealthSeverity.INFO.value,
        confidence=1.0
    )
    
    # Mock KPI 
    mock_kpi = KpiSnapshot(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        target_type="workspace",
        target_id=workspace_id,
        kpi_name="reply_rate",
        current_value=55.0,
        percentage_change=12.5,  # Up by 12.5%
        status=KpiStatus.HEALTHY.value
    )
    
    # Mock an existing active insight to test superseding
    mock_existing_insight = insight_models.InsightSnapshot(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        target_type="workspace",
        target_id=workspace_id,
        generator_name="EngagementImprovementGenerator",
        lifecycle_status=InsightLifecycle.ACTIVE.value
    )
    
    engine = InsightEngine(mock_session)
    engine.health_repo.get_latest_snapshots = AsyncMock(return_value=[mock_health])
    engine.kpi_repo.get_latest_snapshots = AsyncMock(return_value=[mock_kpi])
    
    # It returns an existing active insight when asked
    engine.insight_repo.get_active_insight_by_generator = AsyncMock(return_value=mock_existing_insight)
    
    # Mock save_insight to just return what it was given
    async def mock_save(insight):
        return insight
    engine.insight_repo.save_insight = AsyncMock(side_effect=mock_save)
    engine.insight_repo.supersede_insight = AsyncMock()
    
    with patch("app.domain.insight.engine.insight_registry", mock_registry):
        snapshots = await engine.generate_insights(workspace_id, "workspace", workspace_id)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        
        # Verify basic snapshot
        assert snapshot.category == InsightCategory.PERFORMANCE_IMPROVEMENT.value
        assert snapshot.generator_name == "EngagementImprovementGenerator"
        assert snapshot.lifecycle_status == InsightLifecycle.ACTIVE.value
        
        # Verify Evidence Graph was created
        assert "nodes" in snapshot.evidence_graph
        assert "edges" in snapshot.evidence_graph
        assert len(snapshot.evidence_graph["nodes"]) == 2
        assert len(snapshot.evidence_graph["edges"]) == 1
        
        # Verify node properties
        node_types = [n["node_type"] for n in snapshot.evidence_graph["nodes"]]
        assert "HEALTH" in node_types
        assert "KPI" in node_types
