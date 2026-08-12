import pytest
import uuid
from unittest.mock import AsyncMock

from app.domain.recommendations.models import Recommendation, RecommendationType, RecommendationStatus, RecommendationSource, RecommendationScope, RecommendationPriority, RecommendationConfidence
from app.events.model.intelligence_events import RecommendationCreatedEvent
from app.domain.operations.intelligence.handlers import RecommendationEventHandler
from app.domain.operations.intelligence.models import ActionIntelligenceResult, ActionIntelligenceOutcome

@pytest.mark.asyncio
async def test_handler_successful_processing():
    mock_rec_engine = AsyncMock()
    mock_intel_engine = AsyncMock()

    handler = RecommendationEventHandler(
        recommendation_engine=mock_rec_engine,
        action_intel_engine=mock_intel_engine
    )

    workspace_id = uuid.uuid4()
    rec_id = uuid.uuid4()

    event = RecommendationCreatedEvent(
        workspace_id=workspace_id,
        recommendation_id=rec_id,
        recommendation_type="FOLLOW_UP",
        status="CANDIDATE",
        actor_type="system",
        source_subsystem="recommendation",
        category="ACTION",
        event_name="recommendation.created"
    )

    mock_rec = Recommendation(
        id=rec_id,
        workspace_id=workspace_id,
        type=RecommendationType.FOLLOW_UP,
        status=RecommendationStatus.CANDIDATE,
        source=RecommendationSource.SYSTEM,
        scope=RecommendationScope.CUSTOMER,
        priority=RecommendationPriority.MEDIUM,
        confidence=RecommendationConfidence(value=1.0),
        title="Test",
        description="Test"
    )
    
    mock_rec_engine.get.return_value = mock_rec

    mock_result = ActionIntelligenceResult(
        outcome=ActionIntelligenceOutcome.ACTION_CREATED,
        recommendation_id=rec_id,
        explanation="Success"
    )
    mock_intel_engine.evaluate_recommendation.return_value = mock_result

    await handler.handle_recommendation_created(event)

    mock_rec_engine.get.assert_called_once_with(rec_id)
    mock_intel_engine.evaluate_recommendation.assert_called_once_with(mock_rec)
