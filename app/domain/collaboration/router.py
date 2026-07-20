import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.postgres.database import get_db
from app.domain.collaboration.schemas import (
    CollaborationTaskSchema,
    AutonomyPolicySchema,
    LearningRuleSchema,
    PolicySimulationRequest,
    PolicySimulationResponse,
    FeedbackRequest,
    ApprovalRequest
)
from app.domain.collaboration.repository import CollaborationRepository
from app.domain.collaboration.engines.simulator import PolicySimulator
from app.domain.collaboration.engines.feedback import HumanFeedbackEngine
from app.domain.collaboration.engines.approval import HumanApprovalFramework
from app.domain.collaboration.engines.trust import TrustEngine
from app.domain.collaboration.models import TaskFeedback

router = APIRouter(prefix="/collaboration", tags=["Collaboration"])

@router.get("/tasks", response_model=List[CollaborationTaskSchema])
async def list_tasks(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Lists recent actionable tasks and their routing status."""
    repo = CollaborationRepository(db)
    return await repo.list_tasks(workspace_id)

@router.get("/decision-history", response_model=List[CollaborationTaskSchema])
async def list_decision_history(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Same as tasks but semantically used for the Decision Audit Engine."""
    repo = CollaborationRepository(db)
    # The Task model includes audit_log relation.
    return await repo.list_tasks(workspace_id, limit=100)

@router.get("/autonomy-policies", response_model=List[AutonomyPolicySchema])
async def list_autonomy_policies(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Lists current configured autonomy levels for various intents."""
    # Placeholder query, normally would paginate
    from sqlalchemy.future import select
    from app.domain.collaboration.models import AutonomyPolicy
    result = await db.execute(select(AutonomyPolicy).where(AutonomyPolicy.workspace_id == workspace_id))
    return result.scalars().all()

@router.get("/learning-rules", response_model=List[LearningRuleSchema])
async def list_learning_rules(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Lists extracted learning rules for human approval."""
    repo = CollaborationRepository(db)
    return await repo.get_learning_rules(workspace_id)

@router.post("/simulate-policy", response_model=PolicySimulationResponse)
async def simulate_policy(
    workspace_id: uuid.UUID, 
    req: PolicySimulationRequest, 
    db: AsyncSession = Depends(get_db)
):
    """Simulates impact of moving an intent type to a different autonomy level."""
    repo = CollaborationRepository(db)
    return await PolicySimulator.simulate(repo, workspace_id, req.intent_type, req.proposed_level)

@router.post("/feedback", response_model=dict)
async def submit_feedback(
    req: FeedbackRequest,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Submits human feedback on an AI decision, potentially triggering the Learning Engine."""
    repo = CollaborationRepository(db)
    feedback = TaskFeedback(
        task_id=req.task_id,
        user_id=user_id,
        rating=req.rating,
        comments=req.comments,
        is_override=req.is_override,
        override_details=req.override_details
    )
    await HumanFeedbackEngine.process_feedback(repo, feedback)
    return {"status": "success"}

@router.post("/approve", response_model=CollaborationTaskSchema)
async def process_approval(
    req: ApprovalRequest,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Approves or rejects a task in the human approval chain."""
    repo = CollaborationRepository(db)
    return await HumanApprovalFramework.process_approval(repo, req.task_id, user_id, req.approve)

@router.get("/trust-metrics", response_model=Dict[str, Any])
async def get_trust_metrics(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Returns AI accuracy based on human overrides."""
    repo = CollaborationRepository(db)
    return await TrustEngine.measure_accuracy(repo, workspace_id)
