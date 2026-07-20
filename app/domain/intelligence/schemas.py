from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any


class OperationalHealthSnapshotResponse(BaseModel):
    workspace_id: UUID
    health_index: float
    friction_score: float
    risk_score: float
    leakage_score: float
    
    health_delta: Optional[float]
    friction_delta: Optional[float]
    risk_delta: Optional[float]
    leakage_delta: Optional[float]
    
    trend: str
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeakageEventResponse(BaseModel):
    id: UUID
    leakage_type: str
    revenue_at_risk: float
    currency: str
    description: str
    detected_at: datetime
    is_recovered: bool
    recovered_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RootCauseAnalysisResponse(BaseModel):
    id: UUID
    target_event_type: str
    cause_category: str
    explanation: str
    confidence_score: float
    metadata_json: Dict[str, Any]
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictionEventResponse(BaseModel):
    id: UUID
    prediction_type: str
    description: str
    confidence_score: float
    timeframe_days: int
    predicted_impact: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutiveInsightResponse(BaseModel):
    id: UUID
    insight_type: str
    narrative: str
    priority: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntelligenceSummaryResponse(BaseModel):
    health: OperationalHealthSnapshotResponse
    insights: List[ExecutiveInsightResponse]
    top_leakages: List[LeakageEventResponse]
    top_predictions: List[PredictionEventResponse]
    top_root_causes: List[RootCauseAnalysisResponse]
