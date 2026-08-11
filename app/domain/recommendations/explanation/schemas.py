from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Any, Dict
from enum import Enum
from .models import ExplanationType, ExplanationSectionType, EvidenceReferenceType, ExplanationConfidence

class ExplanationProvenanceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    generated_at: str
    generated_by_system: str
    version: str
    model_version: Optional[str] = None

class ExplanationEvidenceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    reference_type: EvidenceReferenceType
    reference_id: str
    description: str
    value: Any
    impact: str

class PriorityFactorExplanationDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    factor_name: str
    score_contribution: float
    reason: str
    evidence_references: List[str]

class RecommendationExplanationDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    explanation_id: str
    recommendation_id: str
    title: str
    summary: str
    recommendation_reason: str
    priority_reason: str
    evidence: List[ExplanationEvidenceDTO]
    factor_explanations: List[PriorityFactorExplanationDTO]
    limitations: List[str]
    confidence: ExplanationConfidence
    provenance: ExplanationProvenanceDTO
