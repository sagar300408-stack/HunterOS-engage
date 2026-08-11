import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.domain.recommendations.models import Recommendation, RecommendationType, RecommendationStatus, RecommendationSource, RecommendationScope, RecommendationPriority, RecommendationConfidence, RecommendationTarget
from app.domain.operations.intelligence.engine import ActionIntelligenceEngine
from app.domain.operations.intelligence.models import ActionIntelligenceOutcome
from app.domain.operations.exceptions import ActionConflictError
from app.domain.operations.models import Action, ActionType, ActionStatus

@pytest.fixture
def mock_operations_engine():
    engine = AsyncMock()
    return engine

@pytest.fixture
def intelligence_engine(mock_operations_engine):
    return ActionIntelligenceEngine(operations_engine=mock_operations_engine)

@pytest.fixture
def sample_recommendation():
    return Recommendation(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        type=RecommendationType.FOLLOW_UP,
        status=RecommendationStatus.ACTIVE,
        source=RecommendationSource.SYSTEM,
        scope=RecommendationScope.CUSTOMER,
        priority=RecommendationPriority.HIGH,
        confidence=RecommendationConfidence(value=0.9),
        title="Follow up with customer",
        description="The customer requested a follow up.",
        targets=[
            RecommendationTarget(
                target_id=str(uuid.uuid4()),
                target_type="customer"
            )
        ],
        updated_at=datetime.now(timezone.utc)
    )

@pytest.mark.asyncio
async def test_evaluate_recommendation_success(intelligence_engine, mock_operations_engine, sample_recommendation):
    mock_action = MagicMock(spec=Action)
    mock_action.id = uuid.uuid4()
    mock_action.status = ActionStatus.DETECTED
    mock_operations_engine.create_action.return_value = mock_action

    result = await intelligence_engine.evaluate_recommendation(sample_recommendation)
    
    assert result.outcome == ActionIntelligenceOutcome.ACTION_CREATED
    assert result.action_id == mock_action.id
    assert result.requirement.supported_action_type == ActionType.CREATE_FOLLOWUP
    
    # Assert OperationsEngine was called correctly
    mock_operations_engine.create_action.assert_called_once()
    kwargs = mock_operations_engine.create_action.call_args.kwargs
    assert kwargs["workspace_id"] == sample_recommendation.workspace_id
    req = kwargs["request"]
    assert req.action_type == ActionType.CREATE_FOLLOWUP
    assert req.idempotency_key == f"action_intel_rec_{sample_recommendation.id}"
    assert req.provenance.system_source == "ACTION_INTELLIGENCE"
    assert req.provenance.context["recommendation_updated_at"] == sample_recommendation.updated_at.isoformat()
    assert req.evidence[0].content == sample_recommendation.description

@pytest.mark.asyncio
async def test_evaluate_recommendation_unsupported(intelligence_engine, mock_operations_engine, sample_recommendation):
    # Change to an unsupported type
    unsupported_rec = Recommendation(
        id=sample_recommendation.id,
        workspace_id=sample_recommendation.workspace_id,
        type=RecommendationType.CUSTOM,
        status=sample_recommendation.status,
        source=sample_recommendation.source,
        scope=sample_recommendation.scope,
        priority=sample_recommendation.priority,
        confidence=sample_recommendation.confidence,
        title=sample_recommendation.title,
        description=sample_recommendation.description,
        updated_at=sample_recommendation.updated_at
    )
    
    result = await intelligence_engine.evaluate_recommendation(unsupported_rec)
    
    assert result.outcome == ActionIntelligenceOutcome.UNSUPPORTED
    mock_operations_engine.create_action.assert_not_called()

@pytest.mark.asyncio
async def test_evaluate_recommendation_conflict(intelligence_engine, mock_operations_engine, sample_recommendation):
    # Simulate a collision from deduplication
    mock_operations_engine.create_action.side_effect = ActionConflictError("Conflict")

    result = await intelligence_engine.evaluate_recommendation(sample_recommendation)
    
    assert result.outcome == ActionIntelligenceOutcome.ACTION_ALREADY_EXISTS
    assert result.requirement is not None
