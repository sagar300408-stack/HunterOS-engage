from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime

from app.domain.onboarding.models import ProvisioningStatus, IntegrationStatus, GoLiveStatus

class GoLiveAssessmentSchema(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    status: GoLiveStatus
    readiness_score: float
    deployment_confidence: float
    reason: Optional[str]
    evaluated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class IntegrationConnectionSchema(BaseModel):
    id: uuid.UUID
    provider_name: str
    status: IntegrationStatus
    health_score: float
    model_config = ConfigDict(from_attributes=True)

class ImportJobSchema(BaseModel):
    id: uuid.UUID
    entity_type: str
    status: str
    rows_processed: int
    rows_failed: int
    data_quality_score: float
    model_config = ConfigDict(from_attributes=True)

class OperationalCapabilitySchema(BaseModel):
    capability_name: str
    status: str
    reason: Optional[str]
    model_config = ConfigDict(from_attributes=True)

class OnboardingDashboardSummary(BaseModel):
    workspace_readiness: float
    data_quality: float
    integration_health: float
    context_coverage: float
    policy_coverage: float
    automation_readiness: float
    deployment_confidence: float
    golive_status: GoLiveStatus
    capabilities: List[OperationalCapabilitySchema]
