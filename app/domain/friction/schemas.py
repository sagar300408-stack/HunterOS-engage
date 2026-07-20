from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─── SLA Policy ───────────────────────────────────────────────────────────────

class SLAPolicyCreate(BaseModel):
    policy_name: str
    event_trigger: str
    target_metric: str
    description: Optional[str] = None
    warning_threshold_minutes: int
    critical_threshold_minutes: int
    is_active: bool = True


class SLAPolicyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    policy_name: str
    event_trigger: str
    target_metric: str
    description: Optional[str]
    warning_threshold_minutes: int
    critical_threshold_minutes: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Friction Event ───────────────────────────────────────────────────────────

class FrictionEventResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    friction_type: str
    severity: str
    source_entity_type: Optional[str]
    source_entity_id: Optional[UUID]
    score_contribution: float
    expected_value: Optional[float]
    actual_value: Optional[float]
    deviation_pct: Optional[float]
    description: str
    recommendation_hint: Optional[str]
    resolution_status: str
    detected_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Friction Score ───────────────────────────────────────────────────────────

class FrictionScoreResponse(BaseModel):
    workspace_id: UUID
    score: float                           # 0–100; higher = more friction
    previous_score: Optional[float]
    score_delta: Optional[float]
    trend: str                             # IMPROVING / STABLE / DETERIORATING
    contributors: Dict[str, float]         # {friction_type: contribution}
    calculated_at: datetime

    class Config:
        from_attributes = True


class FrictionScoreHistoryItem(BaseModel):
    score: float
    trend: str
    calculated_at: datetime

    class Config:
        from_attributes = True


# ─── Workflow Latency ─────────────────────────────────────────────────────────

class WorkflowLatencyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    stage_name: str
    expected_duration_hours: float
    actual_avg_hours: float
    sample_count: int
    status: str
    delay_factor: float = Field(default=1.0, description="actual / expected — >1 means delayed")
    last_updated: Optional[datetime]

    class Config:
        from_attributes = True


# ─── SLA Compliance ───────────────────────────────────────────────────────────

class SLAComplianceResponse(BaseModel):
    policy: SLAPolicyResponse
    total_events: int
    breached_events: int
    warning_events: int
    compliance_rate_pct: float              # % that passed SLA


# ─── Executive Summary ────────────────────────────────────────────────────────

class TopFrictionSource(BaseModel):
    friction_type: str
    contribution: float
    open_count: int
    description: str


class FrictionSummaryResponse(BaseModel):
    workspace_id: UUID
    business_friction_score: float
    score_trend: str
    score_delta: Optional[float]
    top_friction_sources: List[TopFrictionSource]
    open_friction_events: int
    critical_events: int
    sla_compliance_pct: float
    bottleneck_stages: List[WorkflowLatencyResponse]
    generated_at: datetime


# ─── Trigger Analysis ─────────────────────────────────────────────────────────

class AnalysisTriggerResponse(BaseModel):
    workspace_id: UUID
    friction_events_detected: int
    new_score: float
    previous_score: Optional[float]
    triggered_at: datetime
