import uuid
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
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
from app.domain.marketplace import models as marketplace_models
from app.domain.autonomous import models as autonomous_models

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
    
    # Create mock action
    mock_action = AsyncMock()
    mock_action.id = uuid.uuid4()
    mock_action.status = "READY"
    mock_action.action_type = "send_email"
    mock_action.target = "email"
    mock_action.priority = "HIGH"
    
    mock_action_repo = AsyncMock()
    mock_action_repo.get_action = AsyncMock(return_value=mock_action)
    
    req = SubmitApprovalRequest(
        action_id=mock_action.id,
        context=ApprovalContext(
            action_type="send_email",
            target_system="email",
            risk_level="HIGH"
        ),
        requested_by="test"
    )
    
    needs_approval, approval = await engine.evaluate_action(workspace_id, req, mock_action_repo)
    
    assert needs_approval is True
    assert approval.status == ApprovalStatus.UNDER_REVIEW.value
    assert mock_event_bus.publish.call_count == 2
    
@pytest.mark.asyncio
async def test_authorization_validation():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    engine = ApprovalEngine(mock_session, mock_event_bus)
    
    workspace_id = uuid.uuid4()
    approval_req = approval_models.ApprovalRequest(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        action_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        status=ApprovalStatus.UNDER_REVIEW.value,
        current_stage_index=0,
        requested_by="requester_1",
        requested_at=datetime.now(timezone.utc)
    )
    
    engine.repo.get_request = AsyncMock(return_value=approval_req)
    
    policy = ApprovalPolicy(
        id=approval_req.policy_id,
        workspace_id=workspace_id,
        name="Strict Check",
        enabled=True,
        stages=[{"type": "MANUAL", "approver_ids": ["approver_1", "approver_2"], "required_count": 1}]
    )
    engine.repo.get_policy = AsyncMock(return_value=policy)
    
    req = MakeDecisionRequest(
        approver_id="approver_1",
        decision="APPROVED"
    )
    
    # 1. Reject if authenticated actor doesn't match approver_id from DTO
    with pytest.raises(PermissionError, match="not authorized to act as"):
        await engine.process_decision(approval_req.id, req, authenticated_actor_id="hacker_1")
        
    # 2. Reject if authenticated actor is not in the allowed list for the stage
    req.approver_id = "hacker_1"
    with pytest.raises(PermissionError, match="not authorized to approve stage"):
        await engine.process_decision(approval_req.id, req, authenticated_actor_id="hacker_1")
        
    # 3. Success if authenticated actor matches and is authorized
    req.approver_id = "approver_1"
    
    mock_decision = AsyncMock()
    mock_decision.decision = "APPROVED"
    engine.repo.get_decisions_for_stage = AsyncMock(return_value=[mock_decision])
    
    engine.repo.save_decision = AsyncMock()
    engine.repo.update_request = AsyncMock(side_effect=lambda x: x)
    
    res = await engine.process_decision(approval_req.id, req, authenticated_actor_id="approver_1")
    assert res.status == ApprovalStatus.APPROVED.value

@pytest.mark.asyncio
async def test_action_readiness_prerequisite():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    engine = ApprovalEngine(mock_session, mock_event_bus)
    
    workspace_id = uuid.uuid4()
    
    # Create mock action that is NOT ready
    mock_action = AsyncMock()
    mock_action.id = uuid.uuid4()
    mock_action.status = "EXECUTING" # Not READY or PLANNED
    
    mock_action_repo = AsyncMock()
    mock_action_repo.get_action = AsyncMock(return_value=mock_action)
    
    req = SubmitApprovalRequest(
        action_id=mock_action.id,
        context=ApprovalContext(
            action_type="send_email",
            target_system="email",
            risk_level="HIGH"
        ),
        requested_by="test"
    )
    
    with pytest.raises(ValueError, match="Cannot evaluate governance for action in state EXECUTING"):
        await engine.evaluate_action(workspace_id, req, mock_action_repo)
        
@pytest.mark.asyncio
async def test_workspace_isolation():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    engine = ApprovalEngine(mock_session, mock_event_bus)
    
    workspace_id = uuid.uuid4()
    wrong_workspace_id = uuid.uuid4()
    
    # Create mock action in WRONG workspace
    mock_action = AsyncMock()
    mock_action.id = uuid.uuid4()
    
    mock_action_repo = AsyncMock()
    # Mocking get_action to return None because it doesn't exist in the queried workspace_id
    mock_action_repo.get_action = AsyncMock(return_value=None)
    
    req = SubmitApprovalRequest(
        action_id=mock_action.id,
        context=ApprovalContext(
            action_type="send_email",
            target_system="email",
            risk_level="HIGH"
        ),
        requested_by="test"
    )
    
    with pytest.raises(ValueError, match=f"Action {mock_action.id} not found in workspace {workspace_id}"):
        await engine.evaluate_action(workspace_id, req, mock_action_repo)


