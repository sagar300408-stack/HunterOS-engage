import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.postgres.database import get_db
from app.domain.onboarding.schemas import (
    GoLiveAssessmentSchema,
    OnboardingDashboardSummary,
    OperationalCapabilitySchema
)
from app.domain.onboarding.models import GoLiveStatus
from app.domain.onboarding.repository import OnboardingRepository

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

@router.get("/dashboard", response_model=OnboardingDashboardSummary)
async def get_dashboard(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns the comprehensive Go-Live dashboard including Readiness, Quality, and Capabilities.
    """
    repo = OnboardingRepository(db)
    
    # Mock aggregation for Milestone 5
    return OnboardingDashboardSummary(
        workspace_readiness=96.0,
        data_quality=94.0,
        integration_health=100.0,
        context_coverage=91.0,
        policy_coverage=88.0,
        automation_readiness=93.0,
        deployment_confidence=95.0,
        golive_status=GoLiveStatus.READY,
        capabilities=[
            OperationalCapabilitySchema(capability_name="Business Friction Engine", status="AUTONOMOUS", reason=None),
            OperationalCapabilitySchema(capability_name="Lead Assignment", status="HUMAN_REVIEW", reason="CRM data quality low"),
            OperationalCapabilitySchema(capability_name="Customer Intelligence", status="LIMITED", reason="Missing historical data")
        ]
    )

@router.post("/go-live", response_model=GoLiveAssessmentSchema)
async def evaluate_go_live(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Triggers the Go-Live Readiness Engine to assign a deployment status and confidence score.
    """
    # Mocking a successful Go-Live Assessment for Milestone 5
    from app.domain.onboarding.models import GoLiveAssessment
    from datetime import datetime, timezone
    
    assessment = GoLiveAssessment(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        status=GoLiveStatus.READY,
        readiness_score=96.0,
        deployment_confidence=95.0,
        reason="Business Context Complete. Integrations Healthy. Policies Loaded.",
        evaluated_at=datetime.now(timezone.utc)
    )
    return assessment
