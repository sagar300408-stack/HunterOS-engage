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

# ── R7: Workspace Provisioning ─────────────────────────────────────────────────

class WorkspaceProvisionRequest(BaseModel):
    """Request body for POST /api/v1/workspaces — authenticated platform admin endpoint."""
    workspace_id: Optional[uuid.UUID] = None  # If None, auto-generated
    owner_email: str
    owner_name: str
    owner_password: str

class WorkspaceProvisionResponse(BaseModel):
    workspace_id: uuid.UUID
    status: ProvisioningStatus
    current_step: str
    created_at: datetime
    completed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

# ── R8: Validation Results ─────────────────────────────────────────────────────

class ValidationCheckResult(BaseModel):
    check_name: str
    status: str  # PASS / FAIL / WARNING
    details: Dict[str, Any]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class OnboardingStatusResponse(BaseModel):
    workspace_id: uuid.UUID
    provisioning_status: Optional[str]
    current_step: Optional[str]
    validation_checks: List[ValidationCheckResult]
    has_failures: bool

# ── R9: Readiness Report ───────────────────────────────────────────────────────

class ReadinessCheckItem(BaseModel):
    name: str
    category: str
    status: str  # PASS / FAIL / WARNING
    detail: str
    required: bool

class GoLiveReadinessResponse(BaseModel):
    """Full readiness response with explainable check results."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    status: GoLiveStatus
    readiness_score: float
    deployment_confidence: float
    reason: Optional[str]
    evaluated_at: datetime
    checks: List[ReadinessCheckItem] = []
    not_ready_reasons: List[str] = []
    recommendations: List[str] = []
    model_config = ConfigDict(from_attributes=True)

