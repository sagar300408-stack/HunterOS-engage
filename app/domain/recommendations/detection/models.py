from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from uuid import UUID

# Assume these are provided by the Foundation models
from app.domain.recommendations.models import (
    RecommendationTarget,
    RecommendationType,
    RecommendationConfidence,
    RecommendationSource,
)
from app.domain.recommendations.evidence import EvidenceReference
from app.domain.recommendations.provenance.models import RecommendationProvenance

class DetectionMethod(str, Enum):
    RULE_BASED = "RULE_BASED"
    INTENT_DRIVEN = "INTENT_DRIVEN"
    JOURNEY_DRIVEN = "JOURNEY_DRIVEN"
    CONVERSATION_DRIVEN = "CONVERSATION_DRIVEN"
    MEMORY_DRIVEN = "MEMORY_DRIVEN"
    COMPOSITE = "COMPOSITE"
    CUSTOM = "CUSTOM"

@dataclass(frozen=True)
class RecommendationTrigger:
    trigger_id: str
    trigger_type: str
    description: str
    source_module: str
    source_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class RecommendationCandidate:
    candidate_id: UUID
    workspace_id: UUID
    target: RecommendationTarget
    recommendation_type: RecommendationType
    title: str
    description: str
    confidence: RecommendationConfidence
    source: RecommendationSource
    trigger: RecommendationTrigger
    evidence_references: List[EvidenceReference]
    provenance: RecommendationProvenance
    detected_at: datetime
    rule_id: str
    rule_version: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DetectionDiagnostics:
    pipeline_start: datetime
    pipeline_end: Optional[datetime] = None
    execution_time_ms: Optional[float] = None
    rules_evaluated: int = 0
    rules_matched: int = 0
    candidates_generated: int = 0
    candidates_validated: int = 0
    candidates_rejected: int = 0
    candidates_deduplicated: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class RecommendationDetectionResult:
    detection_id: UUID
    workspace_id: UUID
    target: RecommendationTarget
    candidates: List[RecommendationCandidate]
    diagnostics: DetectionDiagnostics
    provenance: RecommendationProvenance
    detected_at: datetime
    schema_version: str
    engine_version: str
