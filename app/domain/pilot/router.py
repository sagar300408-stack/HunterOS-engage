from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.v1.auth_deps import RequirePermissions, get_current_user
from app.integrations.postgres.database import get_db
from app.domain.pilot.models import PilotDeployment, PilotFeedback, PilotPhase, FeedbackSeverity
from app.domain.pilot.engines.onboarding import PilotOnboardingEngine
from app.domain.pilot.engines.feedback import PilotFeedbackEngine
from app.domain.pilot.engines.roi import PilotROIEngine

router = APIRouter(prefix="/pilots", tags=["Pilot Deployments"])

class InitiatePilotRequest(BaseModel):
    workspace_id: uuid.UUID
    company_name: str
    success_criteria: dict

class FeedbackRequest(BaseModel):
    content: str
    severity: FeedbackSeverity
    business_impact: str

@router.post("", dependencies=[Depends(RequirePermissions("edit_all"))])
async def initiate_pilot(request: InitiatePilotRequest, db: AsyncSession = Depends(get_db)):
    """Initiates a new pilot engagement."""
    pilot = await PilotOnboardingEngine.initiate_pilot(
        db, request.workspace_id, request.company_name, request.success_criteria
    )
    return {"pilot_id": pilot.id, "phase": pilot.phase}

@router.get("", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_pilots(db: AsyncSession = Depends(get_db)):
    """List all pilots."""
    stmt = select(PilotDeployment).order_by(PilotDeployment.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/{pilot_id}/feedback")
async def submit_feedback(pilot_id: uuid.UUID, request: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    """Submit continuous feedback for a pilot."""
    feedback = await PilotFeedbackEngine.submit_feedback(
        db, pilot_id, request.content, request.severity, request.business_impact
    )
    return {"feedback_id": feedback.id, "status": "submitted"}

@router.get("/{pilot_id}/roi", dependencies=[Depends(RequirePermissions("view_all"))])
async def get_executive_roi_report(pilot_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Generates the Executive ROI validation report."""
    return await PilotROIEngine.generate_executive_report(db, pilot_id)
