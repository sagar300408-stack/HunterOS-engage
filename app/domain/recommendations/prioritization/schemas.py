from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from .models import (
    PriorityLevel, UrgencyLevel, ImpactLevel, EvidenceStrength, 
    FreshnessLevel, BlockingLevel, PriorityFactorType, 
    PrioritizationMethod, TieResolutionMethod
)

class PriorityFactorSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    factor_type: PriorityFactorType
    score: float = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)
    evidence: str
    strength: EvidenceStrength

class PriorityScoreSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    total_score: float
    normalized_score: float = Field(..., ge=0, le=100)
    level: PriorityLevel
    urgency: UrgencyLevel
    impact: ImpactLevel
    factors: List[PriorityFactorSchema] = Field(default_factory=list)

class PriorityAssessmentSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    assessment_id: str
    method: PrioritizationMethod
    score: PriorityScoreSchema
    assessed_at: datetime
    assessor_id: str

class RecommendationCandidateSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    candidate_id: str
    content: str
    workspace_id: str

class PrioritizedRecommendationSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    candidate: RecommendationCandidateSchema
    assessment: PriorityAssessmentSchema
    rank: int = Field(..., ge=1)

class RecommendationPrioritizationResultSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    result_id: str
    workspace_id: str
    recommendations: List[PrioritizedRecommendationSchema]
    created_at: datetime
    method_used: PrioritizationMethod
