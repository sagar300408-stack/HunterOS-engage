import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.domain.recommendation.engine import RecommendationEngine
from app.domain.recommendation.generators.standard_recommendations import DecliningEngagementGenerator
from app.domain.recommendation.models import RecommendationLifecycle, RecommendationCategory
from app.domain.insight.models import InsightSnapshot, InsightCategory

# SQLAlchemy mapping requirements
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
async def test_recommendation_engine_generates_and_supersedes():
    mock_session = AsyncMock()
    workspace_id = uuid.uuid4()
    
    mock_registry = MagicMock()
    mock_registry.get_all_generators.return_value = [DecliningEngagementGenerator()]
    
    # Mock Insight 
    mock_insight = InsightSnapshot(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        target_type="workspace",
        target_id=workspace_id,
        title="Engagement Drop",
        category=InsightCategory.PERFORMANCE_DECLINE.value,
        related_health_objects=["customer_engagement_health"],
        related_kpis=["reply_rate"]
    )
    
    # Mock an existing active recommendation to test superseding
    mock_existing_rec = rec_models.RecommendationSnapshot(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        target_type="workspace",
        target_id=workspace_id,
        generator_name="DecliningEngagementGenerator",
        lifecycle_status=RecommendationLifecycle.ACTIVE.value
    )
    
    engine = RecommendationEngine(mock_session)
    engine.insight_repo.get_latest_insights = AsyncMock(return_value=[mock_insight])
    
    # It returns an existing active recommendation when asked
    engine.recommendation_repo.get_active_recommendation_by_generator = AsyncMock(return_value=mock_existing_rec)
    
    # Mock save_recommendation to just return what it was given
    async def mock_save(rec):
        return rec
    engine.recommendation_repo.save_recommendation = AsyncMock(side_effect=mock_save)
    engine.recommendation_repo.supersede_recommendation = AsyncMock()
    
    with patch("app.domain.recommendation.engine.recommendation_registry", mock_registry):
        snapshots = await engine.generate_recommendations(workspace_id, "workspace", workspace_id)
        
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        
        # Verify basic snapshot
        assert snapshot.category == RecommendationCategory.FOLLOWUP_STRATEGY.value
        assert snapshot.generator_name == "DecliningEngagementGenerator"
        assert snapshot.lifecycle_status == RecommendationLifecycle.ACTIVE.value
        
        # Verify Decision Trace was created properly
        assert "insight_ids" in snapshot.decision_trace
        assert len(snapshot.decision_trace["insight_ids"]) == 1
        assert snapshot.decision_trace["insight_ids"][0] == str(mock_insight.id)
        
        # Verify Suggested Actions
        assert len(snapshot.suggested_actions) == 1
        assert snapshot.suggested_actions[0]["action_type"] == "UPDATE_FOLLOWUP_STRATEGY"
