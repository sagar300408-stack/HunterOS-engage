import uuid
import pytest
from unittest.mock import AsyncMock

from app.domain.approval.engine import ApprovalEngine
from app.domain.approval.schemas import SubmitApprovalRequest, ApprovalContext, MakeDecisionRequest
from app.domain.approval.models import ApprovalPolicy, ApprovalStatus
from app.domain.approval.evaluator import PolicyEvaluator

# SQLAlchemy mapping requirements
from app.domain.action import models as action_models
from app.domain.integration import models as integration_models
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
from app.domain.approval import models as approval_models

@pytest.mark.asyncio
async def test_policy_evaluator():
    policy = ApprovalPolicy(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="High Risk Check",
        enabled=True,
        matching_conditions=[
            {"field": "risk", "operator": "==", "value": "HIGH"}
        ]
    )
    
    # Matches
    assert PolicyEvaluator.evaluate(policy, {"risk": "HIGH"}) == True
    
    # Does not match
    assert PolicyEvaluator.evaluate(policy, {"risk": "LOW"}) == False


@pytest.mark.asyncio
async def test_approval_engine_evaluate():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    
    engine = ApprovalEngine(mock_session, mock_event_bus)
    
    workspace_id = uuid.uuid4()
    
    policy = ApprovalPolicy(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name="High Risk Check",
        enabled=True,
        matching_conditions=[
            {"field": "risk", "operator": "==", "value": "HIGH"}
        ]
    )
    
    engine.repo.get_all_active_policies = AsyncMock(return_value=[policy])
    
    async def mock_save(req):
        req.id = uuid.uuid4()
        return req
        
    engine.repo.save_request = AsyncMock(side_effect=mock_save)
    engine.repo.update_request = AsyncMock(side_effect=lambda x: x)
    
    req = SubmitApprovalRequest(
        action_id=uuid.uuid4(),
        context=ApprovalContext(
            action_type="send_email",
            target_system="email",
            risk_level="HIGH"
        ),
        requested_by="test"
    )
    
    needs_approval, approval = await engine.evaluate_action(workspace_id, req)
    
    assert needs_approval is True
    assert approval.status == ApprovalStatus.UNDER_REVIEW.value
    assert mock_event_bus.publish.call_count == 2
