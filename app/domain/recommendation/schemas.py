from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.domain.recommendation.models import (
    RecommendationCategory, ExpectedImpactCategory, 
    RecommendationPriority, RecommendationRisk, 
    RecommendationLifecycle
)


class SuggestedAction(BaseModel):
    action_type: str
    description: str
    target_entity: Optional[str] = None
    parameters: Dict[str, Any] = {}


class DecisionTrace(BaseModel):
    insight_ids: List[str] = []
    health_ids: List[str] = []
    kpi_ids: List[str] = []
    timeline_event_ids: List[str] = []
    explanation: Optional[str] = None


class RecommendationGeneratorDefinition(BaseModel):
    name: str
    version: str = "1.0"
    description: str


class RecommendationSnapshotResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    target_type: str
    target_id: UUID
    
    title: str
    summary: str
    
    category: str
    expected_impact: str
    priority: str
    risk_level: str
    
    lifecycle_status: str
    expires_at: Optional[datetime] = None
    
    recommendation_score: float
    confidence: float
    
    suggested_actions: List[Dict[str, Any]]
    decision_trace: Dict[str, Any]
    
    generator_name: str
    generator_version: str
    trigger_source: str
    
    generated_at: datetime
    last_updated: datetime

    class Config:
        from_attributes = True


class RecommendationCalculationResult(BaseModel):
    title: str
    summary: str
    category: RecommendationCategory
    expected_impact: ExpectedImpactCategory
    priority: RecommendationPriority
    risk_level: RecommendationRisk
    
    recommendation_score: float
    confidence: float
    
    expires_at: Optional[datetime] = None
    
    suggested_actions: List[SuggestedAction]
    decision_trace: DecisionTrace
