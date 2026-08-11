from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

class ExplanationType(Enum):
    EXECUTIVE = "EXECUTIVE"
    SALES = "SALES"
    OPERATIONS = "OPERATIONS"
    AUDIT = "AUDIT"
    BASE = "BASE"

class ExplanationSectionType(Enum):
    SUMMARY = "SUMMARY"
    RECOMMENDATION_REASON = "RECOMMENDATION_REASON"
    PRIORITY_REASON = "PRIORITY_REASON"
    EVIDENCE = "EVIDENCE"
    LIMITATIONS = "LIMITATIONS"

class EvidenceReferenceType(Enum):
    METRIC = "METRIC"
    EVENT = "EVENT"
    ATTRIBUTE = "ATTRIBUTE"
    RULE = "RULE"
    HEURISTIC = "HEURISTIC"

class ExplanationConfidence(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

@dataclass(frozen=True)
class ExplanationProvenance:
    generated_at: str
    generated_by_system: str
    version: str
    model_version: Optional[str] = None

@dataclass(frozen=True)
class ExplanationEvidence:
    reference_type: EvidenceReferenceType
    reference_id: str
    description: str
    value: Any
    impact: str

@dataclass(frozen=True)
class PriorityFactorExplanation:
    factor_name: str
    score_contribution: float
    reason: str
    evidence_references: List[str]

@dataclass(frozen=True)
class RecommendationExplanation:
    explanation_id: str
    recommendation_id: str
    title: str
    summary: str
    recommendation_reason: str
    priority_reason: str
    evidence: List[ExplanationEvidence]
    factor_explanations: List[PriorityFactorExplanation]
    limitations: List[str]
    confidence: ExplanationConfidence
    provenance: ExplanationProvenance
