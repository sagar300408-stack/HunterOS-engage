from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.health.models import HealthStatus, HealthSeverity, HealthTrend


class HealthDefinition(BaseModel):
    name: str
    description: str
    version: str = "1.0"
    required_kpis: List[str]


class HealthSnapshotResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    target_type: str
    target_id: UUID
    
    health_name: str
    description: Optional[str] = None
    
    current_score: float
    previous_score: Optional[float] = None
    
    trend: str
    status: str
    severity: str
    
    confidence: float
    evaluation_version: str
    
    related_kpis: List[str]
    supporting_evidence: Dict[str, Any]
    
    calculated_at: datetime
    last_updated: datetime

    class Config:
        from_attributes = True


class HealthCalculationResult(BaseModel):
    current_score: float
    previous_score: Optional[float] = None
    status: HealthStatus
    severity: HealthSeverity
    trend: HealthTrend
    confidence: float
    supporting_evidence: Dict[str, Any]
