from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime

from app.domain.impact.models import ImpactCategory, ReportFrequency

class FinancialConfigBase(BaseModel):
    average_hourly_cost: float
    average_deal_value: float
    conversion_rate: float

class FinancialConfigResponse(FinancialConfigBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

class BusinessTargetBase(BaseModel):
    kpi_name: str
    target_value: float
    condition: str

class BusinessTargetResponse(BusinessTargetBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

class BaselineMetricBase(BaseModel):
    metric_name: str
    baseline_value: float

class BaselineMetricResponse(BaselineMetricBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

class EvidenceTraceSchema(BaseModel):
    sequence_order: int
    evidence_text: str
    model_config = ConfigDict(from_attributes=True)

class ValueAttributionSchema(BaseModel):
    id: uuid.UUID
    category: ImpactCategory
    raw_metric_name: Optional[str]
    raw_metric_value: Optional[float]
    estimated_financial_value: float
    currency: str
    confidence_score: float
    evidence_traces: List[EvidenceTraceSchema] = []
    model_config = ConfigDict(from_attributes=True)

class ImpactSummaryResponse(BaseModel):
    overall_roi: float
    currency: str
    revenue_protected: float
    cost_reduction: float
    hours_saved: float
    business_friction_score: float
    operational_health_index: float
    forecast_quarterly_savings: float
    executive_narrative: str
    goals_status: List[Dict[str, Any]]
    top_recommendation: Optional[str]
    top_risk: Optional[str]

class ExecutiveReportResponse(BaseModel):
    id: uuid.UUID
    frequency: ReportFrequency
    start_date: datetime
    end_date: datetime
    narrative_text: str
    data_snapshot: Dict[str, Any]
    model_config = ConfigDict(from_attributes=True)
