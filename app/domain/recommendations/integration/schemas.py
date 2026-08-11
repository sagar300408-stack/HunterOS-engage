from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from .models import ContextCompletenessStatus

class ContextMetadataDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: str
    generated_at: datetime
    source_system: str

class ContextProvenanceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    lineage_id: str
    upstream_ids: List[str]
    assembly_timestamp: datetime

class ContextDiagnosticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    execution_time_ms: float
    warnings: List[str]
    errors: List[str]

class ContextCompletenessReportDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: ContextCompletenessStatus
    missing_modules: List[str]
    present_modules: List[str]

class RecommendationIntelligenceContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    identity_id: str
    metadata: ContextMetadataDTO
    provenance: ContextProvenanceDTO
    diagnostics: ContextDiagnosticsDTO
    completeness: ContextCompletenessReportDTO
    candidate_data: Optional[Dict[str, Any]] = None
    prioritization_data: Optional[Dict[str, Any]] = None
    explanation_data: Optional[Dict[str, Any]] = None

class ExecutiveRecommendationContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: RecommendationIntelligenceContextDTO
    executive_summary: str
    action_required: bool

class StandardAPIRecommendationContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: RecommendationIntelligenceContextDTO
    api_version: str
