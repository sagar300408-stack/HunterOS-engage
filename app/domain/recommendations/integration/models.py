from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

class ContextCompletenessStatus(Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INCOMPLETE = "INCOMPLETE"
    DEGRADED = "DEGRADED"

@dataclass(frozen=True)
class ContextMetadata:
    version: str
    generated_at: datetime
    source_system: str

@dataclass(frozen=True)
class ContextProvenance:
    lineage_id: str
    upstream_ids: List[str]
    assembly_timestamp: datetime

@dataclass(frozen=True)
class ContextDiagnostics:
    execution_time_ms: float
    warnings: List[str]
    errors: List[str]

@dataclass(frozen=True)
class ContextCompletenessReport:
    status: ContextCompletenessStatus
    missing_modules: List[str]
    present_modules: List[str]

@dataclass(frozen=True)
class RecommendationIntelligenceContext:
    identity_id: str
    metadata: ContextMetadata
    provenance: ContextProvenance
    diagnostics: ContextDiagnostics
    completeness: ContextCompletenessReport
    candidate_data: Optional[Dict[str, Any]] = None
    prioritization_data: Optional[Dict[str, Any]] = None
    explanation_data: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class RecommendationIntegrationArtifact:
    artifact_id: str
    context: RecommendationIntelligenceContext
    created_at: datetime
