from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime

class JourneyIntelligenceBlockType(str, Enum):
    JOURNEY_STATE = "JOURNEY_STATE"
    CURRENT_STAGE = "CURRENT_STAGE"
    STAGE_HISTORY = "STAGE_HISTORY"
    TRANSITION_HISTORY = "TRANSITION_HISTORY"
    TIMELINE = "TIMELINE"
    DEFINITION = "DEFINITION"
    MATURITY = "MATURITY"
    MOMENTUM = "MOMENTUM"
    STABILITY = "STABILITY"
    RESIDENCY = "RESIDENCY"
    VELOCITY = "VELOCITY"
    HEALTH = "HEALTH"
    OBSERVED_OUTCOMES = "OBSERVED_OUTCOMES"
    ANALYTICS = "ANALYTICS"
    TRENDS = "TRENDS"
    COHORTS = "COHORTS"
    CUSTOM = "CUSTOM"

class JourneyContextStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INCOMPLETE = "INCOMPLETE"
    DEGRADED = "DEGRADED"

@dataclass(frozen=True)
class JourneyContextMetadata:
    context_id: str
    context_version: str
    generated_at: datetime
    schema_version: str
    workspace_id: str
    entity_id: str
    entity_type: str
    source_modules: List[str] = field(default_factory=list)
    pipeline_version: Optional[str] = None
    gateway_version: Optional[str] = None

@dataclass(frozen=True)
class JourneyContextCompletenessReport:
    score: float
    status: JourneyContextStatus
    requested_blocks: List[str] = field(default_factory=list)
    loaded_blocks: List[str] = field(default_factory=list)
    missing_blocks: List[str] = field(default_factory=list)
    missing_fields: Dict[str, List[str]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    is_valid: bool = True

@dataclass(frozen=True)
class JourneyContextDiagnostics:
    stage_timings: Dict[str, float] = field(default_factory=dict)
    total_execution_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    source_counts: Dict[str, int] = field(default_factory=dict)
    cache_hit: bool = False
    cache_miss: bool = False

@dataclass(frozen=True)
class JourneyContextBlock:
    block_type: JourneyIntelligenceBlockType
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class JourneyMaturityContext:
    score: float
    level: str
    metrics: Dict[str, float] = field(default_factory=dict)

@dataclass(frozen=True)
class JourneyHistoryContext:
    history_records: List[Dict[str, Any]] = field(default_factory=list)

@dataclass(frozen=True)
class JourneyTimelineContext:
    events: List[Dict[str, Any]] = field(default_factory=list)

@dataclass(frozen=True)
class JourneyAnalyticsContext:
    metrics: Dict[str, Any] = field(default_factory=dict)
    trends: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class JourneyDefinitionContext:
    definition_id: str
    version: str
    stages: List[Dict[str, Any]] = field(default_factory=list)

@dataclass(frozen=True)
class JourneyIntelligenceContext:
    metadata: JourneyContextMetadata
    journey_state: Dict[str, Any]
    completeness: JourneyContextCompletenessReport
    diagnostics: JourneyContextDiagnostics
    maturity: Optional[JourneyMaturityContext] = None
    history: Optional[JourneyHistoryContext] = None
    timeline: Optional[JourneyTimelineContext] = None
    analytics: Optional[JourneyAnalyticsContext] = None
    definition: Optional[JourneyDefinitionContext] = None
    blocks: List[JourneyContextBlock] = field(default_factory=list)

@dataclass(frozen=True)
class JourneyIntelligenceRequestOptions:
    requested_blocks: List[JourneyIntelligenceBlockType] = field(default_factory=list)
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
