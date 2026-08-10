from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.domain.journey.integration.models import (
    JourneyIntelligenceBlockType,
    JourneyContextStatus
)

class JourneyContextMetadataDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    context_id: str
    context_version: str
    generated_at: datetime
    schema_version: str
    workspace_id: str
    entity_id: str
    entity_type: str
    source_modules: List[str] = Field(default_factory=list)
    pipeline_version: Optional[str] = None
    gateway_version: Optional[str] = None

class JourneyContextCompletenessReportDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    score: float
    status: JourneyContextStatus
    requested_blocks: List[str] = Field(default_factory=list)
    loaded_blocks: List[str] = Field(default_factory=list)
    missing_blocks: List[str] = Field(default_factory=list)
    missing_fields: Dict[str, List[str]] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    is_valid: bool = True

class JourneyContextDiagnosticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    stage_timings: Dict[str, float] = Field(default_factory=dict)
    total_execution_time_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    source_counts: Dict[str, int] = Field(default_factory=dict)
    cache_hit: bool = False
    cache_miss: bool = False

class JourneyContextBlockDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    block_type: JourneyIntelligenceBlockType
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class JourneyMaturityContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    score: float
    level: str
    metrics: Dict[str, float] = Field(default_factory=dict)

class JourneyHistoryContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    history_records: List[Dict[str, Any]] = Field(default_factory=list)

class JourneyTimelineContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    events: List[Dict[str, Any]] = Field(default_factory=list)

class JourneyAnalyticsContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    metrics: Dict[str, Any] = Field(default_factory=dict)
    trends: Dict[str, Any] = Field(default_factory=dict)

class JourneyDefinitionContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    definition_id: str
    version: str
    stages: List[Dict[str, Any]] = Field(default_factory=list)

class JourneyIntelligenceContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    metadata: JourneyContextMetadataDTO
    journey_state: Dict[str, Any]
    completeness: JourneyContextCompletenessReportDTO
    diagnostics: JourneyContextDiagnosticsDTO
    maturity: Optional[JourneyMaturityContextDTO] = None
    history: Optional[JourneyHistoryContextDTO] = None
    timeline: Optional[JourneyTimelineContextDTO] = None
    analytics: Optional[JourneyAnalyticsContextDTO] = None
    definition: Optional[JourneyDefinitionContextDTO] = None
    blocks: List[JourneyContextBlockDTO] = Field(default_factory=list)

class ExecutiveJourneyContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: JourneyIntelligenceContextDTO
    executive_summary: Dict[str, Any]

class SalesJourneyContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: JourneyIntelligenceContextDTO
    sales_recommendations: List[str]

class OperationsJourneyContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: JourneyIntelligenceContextDTO
    operational_metrics: Dict[str, Any]

class AuditJourneyContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: JourneyIntelligenceContextDTO
    audit_trail: List[Dict[str, Any]]

class CustomJourneyContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: JourneyIntelligenceContextDTO
    custom_data: Dict[str, Any]

class StandardJourneyContextExportDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: JourneyIntelligenceContextDTO
    export_format: str = "json"

class DashboardJourneyContextExportDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: JourneyIntelligenceContextDTO
    dashboard_widgets: List[Dict[str, Any]]

class AIReadyJourneyContextExportDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: JourneyIntelligenceContextDTO
    embeddings: List[float] = Field(default_factory=list)
    prompt_context: str = ""

class JourneyIntelligenceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    requested_blocks: List[JourneyIntelligenceBlockType] = Field(default_factory=list)
    journey_id: Optional[str] = None
    workspace_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    journey_type: Optional[str] = None
    journey_definition: Optional[str] = None
    observation_window: Optional[str] = None
    cohort: Optional[str] = None
    include_history: bool = False
    include_timeline: bool = False
    include_analytics: bool = False
    include_maturity: bool = False
    include_outcomes: bool = False
    view_mode: Optional[str] = None

class JourneyContextQueryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    query: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    workspace_id: str

class JourneyContextExportRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    context_id: str
    export_type: str
    workspace_id: str
