import pytest
import uuid
from unittest.mock import AsyncMock

from app.domain.recommendations.models import Recommendation, RecommendationType, RecommendationStatus, RecommendationSource, RecommendationScope, RecommendationPriority, RecommendationConfidence
from app.events.model.intelligence_events import RecommendationCreatedEvent
from app.domain.operations.intelligence.handlers import RecommendationEventHandler

@pytest.mark.asyncio
async def test_workspace_isolation_blocks_mismatched_workspaces():
    # Setup mock engines
    mock_rec_engine = AsyncMock()
    mock_intel_engine = AsyncMock()

    handler = RecommendationEventHandler(
        recommendation_engine=mock_rec_engine,
        action_intel_engine=mock_intel_engine
    )

    event_workspace = uuid.uuid4()
    malicious_workspace = uuid.uuid4()
    rec_id = uuid.uuid4()

    event = RecommendationCreatedEvent(
        workspace_id=event_workspace,
        recommendation_id=rec_id,
        recommendation_type="FOLLOW_UP",
        status="PROPOSED"
    )

    # Return a recommendation that belongs to a DIFFERENT workspace
    mock_rec_engine.get.return_value = Recommendation(
        id=rec_id,
        workspace_id=malicious_workspace,
        type=RecommendationType.FOLLOW_UP,
        status=RecommendationStatus.PROPOSED,
        source=RecommendationSource.SYSTEM,
        scope=RecommendationScope.CUSTOMER,
        priority=RecommendationPriority.NORMAL,
        confidence=RecommendationConfidence(value=1.0),
        title="Test",
        description="Test"
    )

    await handler.handle_recommendation_created(event)

    # Ensure evaluate_recommendation was NEVER called because workspace IDs did not match
    mock_intel_engine.evaluate_recommendation.assert_not_called()
