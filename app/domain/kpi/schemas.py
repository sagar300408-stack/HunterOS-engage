from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.kpi.models import KpiCategory, KpiDirection, KpiStatus, KpiTrend, KpiUnit


class KpiDefinition(BaseModel):
    name: str
    category: KpiCategory
    description: str
    unit: KpiUnit
    direction: KpiDirection
    target: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    data_source: str
    refresh_strategy: str


class KpiSnapshotResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    target_type: str
    target_id: UUID
    
    kpi_name: str
    category: str
    description: Optional[str] = None
    unit: str
    direction: str
    
    current_value: float
    previous_value: Optional[float] = None
    percentage_change: Optional[float] = None
    
    trend: str
    status: str
    
    target: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    
    confidence: Optional[float] = None
    data_source: str
    refresh_strategy: str
    
    calculated_at: datetime
    last_updated: datetime

    class Config:
        from_attributes = True


class KpiCalculationResult(BaseModel):
    current_value: float
    previous_value: Optional[float] = None
    percentage_change: Optional[float] = None
    confidence: Optional[float] = None
