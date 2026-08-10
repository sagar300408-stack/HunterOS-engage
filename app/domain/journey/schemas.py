from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class JourneyEvidenceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    evidence_id: str
    evidence_type: str
    source_id: str
    source_module: str
    timestamp: datetime
    description: str
    confidence: float
    metadata: Dict[str, Any]

class ConfidenceFactorsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    intent_match: float = 0.0
    timeline_match: float = 0.0
    conversation_match: float = 0.0
    rule_strength: float = 0.0
    evidence_count_factor: float = 0.0
    evidence_quality_factor: float = 0.0
    source_consistency_factor: float = 0.0
    recency_factor: float = 0.0

class JourneyTransitionDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    transition_id: str
    journey_instance_id: str
    from_stage: Optional[str]
    to_stage: str
    transition_type: str
    occurred_at: datetime
    evidence: List[JourneyEvidenceDTO]
    confidence: float
    confidence_factors: Optional[ConfidenceFactorsDTO]
    reason: str

class JourneyTimelineEventDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_id: str
    event_type: str
    stage: Optional[str]
    previous_stage: Optional[str]
    timestamp: datetime
    confidence: float

class JourneyTimelineDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    timeline_id: str
    events: List[JourneyTimelineEventDTO]

class StageDefinitionDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage_id: str
    stage_code: str
    name: str
    description: str
    sequence: int
    allowed_previous_stages: List[str]
    allowed_next_stages: List[str]
    is_terminal: bool
    is_entry_stage: bool

class JourneyDefinitionDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    journey_id: str
    journey_type: str
    name: str
    description: str
    version: str
    stages: List[StageDefinitionDTO]
    entry_stage: str
    terminal_stages: List[str]

class JourneyStageDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    current_stage: str
    previous_stage: Optional[str]
    stage_entered_at: datetime
    journey_status: str

class JourneyStateDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    journey_instance_id: str
    workspace_id: Optional[str]
    entity_type: str
    entity_id: str
    journey_definition_id: str
    current_stage: str
    previous_stage: Optional[str]
    stage_entered_at: datetime
    journey_started_at: datetime
    last_transition_at: Optional[datetime]
    status: str
    stage_history: List[str]

class JourneyProgressionResultDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    progression_id: str
    journey_instance_id: str
    did_progress: bool
    previous_stage: Optional[str]
    current_stage: str
    new_stage: Optional[str]
    transition: Optional[JourneyTransitionDTO]
    confidence: float
    confidence_factors: Optional[ConfidenceFactorsDTO]
    evidence: List[JourneyEvidenceDTO]
    diagnostics: Dict[str, Any]
    generated_at: datetime

class JourneyDiagnosticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    pipeline_version: str
    rules_evaluated: int
    rules_matched: int
    candidate_transition_count: int
    accepted_transition_count: int
    rejected_transition_count: int
    evidence_count: int
    execution_time_ms: float
    validation_errors: List[str]


# ── Phase 2.4.3: Journey Maturity & Observed Probability DTOs ────────────────


class MaturityFactorsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage_position_factor: float = 0.0
    stage_completion_factor: float = 0.0
    transition_history_factor: float = 0.0
    evidence_strength_factor: float = 0.0
    journey_age_factor: float = 0.0
    stage_stability_factor: float = 0.0
    progression_consistency_factor: float = 0.0
    custom_factors: Dict[str, float] = Field(default_factory=dict)


class JourneyMaturityProvenanceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    calculation_id: str
    journey_id: str
    workspace_id: str
    entity_id: str
    engine_version: str
    pipeline_version: str
    configuration_version: str
    generated_at: datetime
    source_modules: List[str]
    source_artifacts: List[str]
    calculation_method: str
    correlation_id: Optional[str] = None


class JourneyMaturityDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    maturity_score: float
    maturity_level: str
    current_stage: str
    stage_position: int
    total_active_stages: int
    completed_stage_count: int
    journey_progress_ratio: float
    stage_duration_days: float
    journey_age_days: float
    evidence_strength: float
    calculated_at: datetime
    factors: MaturityFactorsDTO
    provenance: JourneyMaturityProvenanceDTO


class JourneyMomentumDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: str
    momentum_score: float
    recent_advancements_count: int
    recent_regressions_count: int
    days_since_last_transition: float
    transition_frequency_per_week: float
    description: str
    calculated_at: datetime


class JourneyStabilityDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    stability_score: float
    stability_level: str
    current_stage_duration_days: float
    stage_reentry_count: int
    stage_transition_count: int
    supporting_evidence_count: int
    conflicting_evidence_count: int
    calculated_at: datetime
    factors: Dict[str, float] = Field(default_factory=dict)


class StageResidencyDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    residency_id: str
    stage: str
    entered_at: datetime
    exited_at: Optional[datetime] = None
    duration_days: float
    transition_count: int
    reentry_count: int
    evidence_count: int
    confidence: float
    status: str


class StageVelocityDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    transitions_per_day: float
    transitions_per_week: float
    average_stage_duration_days: float
    current_stage_duration_days: float
    historical_average_duration_days: Optional[float] = None
    velocity_state: str
    calculated_at: datetime


class ObservedJourneyProbabilityDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    probability_id: str
    value: Optional[float] = None
    status: str
    probability_type: str = "HISTORICAL_OBSERVED"
    target_stage: Optional[str] = None
    target_outcome: str = "CLOSED_WON"
    sample_size: int = 0
    success_count: int = 0
    failure_count: int = 0
    minimum_required_sample: int = 30
    minimum_sample_met: bool = False
    observation_window_days: int = 365
    calculation_method: str = "WILSON_SCORE_INTERVAL"
    confidence: float = 0.0
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    confidence_level: float = 0.95
    cohort_filters: Dict[str, Any] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    calculated_at: datetime


ObservedProbabilityDTO = ObservedJourneyProbabilityDTO


class JourneyHealthDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: str
    summary: str
    factors: Dict[str, Any] = Field(default_factory=dict)
    calculated_at: datetime


class JourneyMaturityDiagnosticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage_timings: Dict[str, float]
    total_execution_time_ms: float
    evidence_count: int
    transition_count: int
    residency_count: int
    rules_evaluated: int
    rules_matched: int
    warnings: List[str]
    validation_errors: List[str]
    probability_available: bool
    probability_sample_size: int
    calculation_version: str


class JourneyMaturityResultDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    journey_id: str
    workspace_id: str
    entity_id: str
    current_stage: str
    journey_status: str
    maturity: JourneyMaturityDTO
    momentum: JourneyMomentumDTO
    stability: JourneyStabilityDTO
    velocity: StageVelocityDTO
    stage_residency: List[StageResidencyDTO]
    current_residency: StageResidencyDTO
    observed_probability: Optional[ObservedJourneyProbabilityDTO] = None
    health: JourneyHealthDTO
    diagnostics: JourneyMaturityDiagnosticsDTO
    provenance: JourneyMaturityProvenanceDTO
    calculated_at: datetime


# Request models
class CreateJourneyRequest(BaseModel):
    workspace_id: str
    entity_type: str = 'CUSTOMER'
    entity_id: str
    journey_type: str = 'SALES'
    journey_definition_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ProgressJourneyRequest(BaseModel):
    workspace_id: Optional[str] = None
    entity_type: str = 'CUSTOMER'
    entity_id: str = ''
    intent_context: Optional[Dict[str, Any]] = None
    conversation_context: Optional[Dict[str, Any]] = None
    memory_context: Optional[Dict[str, Any]] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

class QueryJourneysRequest(BaseModel):
    workspace_id: Optional[str] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    entity_type: Optional[str] = None


class EvaluateMaturityRequest(BaseModel):
    workspace_id: Optional[str] = None
    configuration_version: Optional[str] = None
    cohort_filters: Optional[Dict[str, Any]] = None


class QueryMaturityRequest(BaseModel):
    workspace_id: str
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    maturity_level: Optional[str] = None


class CalculateObservedProbabilityRequest(BaseModel):
    workspace_id: str
    target_stage: Optional[str] = None
    target_outcome: str = "CLOSED_WON"
    minimum_sample: Optional[int] = None
    observation_window_days: int = 365
    cohort_filters: Optional[Dict[str, Any]] = None


# ── Phase 2.4.4: Journey Analytics DTOs ──────────────────────────────────────


class AnalyticsObservationWindowDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    start_at: datetime
    end_at: datetime
    timezone: str = "UTC"
    duration_days: float


class JourneyDistributionDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    total_journeys: int
    active_journeys: int
    completed_journeys: int
    cancelled_journeys: int
    inactive_journeys: int
    archived_journeys: int
    by_journey_type: Dict[str, Any] = Field(default_factory=dict)
    by_status: Dict[str, Any] = Field(default_factory=dict)
    by_current_stage: Dict[str, Any] = Field(default_factory=dict)
    by_maturity_level: Dict[str, Any] = Field(default_factory=dict)
    by_momentum_state: Dict[str, Any] = Field(default_factory=dict)
    by_stability_level: Dict[str, Any] = Field(default_factory=dict)
    by_velocity_state: Dict[str, Any] = Field(default_factory=dict)
    by_health_state: Dict[str, Any] = Field(default_factory=dict)


class StageAnalyticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage: str
    journey_count: int
    percentage_of_journeys: float
    unique_entries: int
    unique_exits: int
    current_residency_count: int
    completed_residency_count: int
    average_residency_days: Optional[float] = None
    median_residency_days: Optional[float] = None
    minimum_residency_days: Optional[float] = None
    maximum_residency_days: Optional[float] = None
    p25_residency_days: Optional[float] = None
    p75_residency_days: Optional[float] = None


class TransitionPairDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    from_stage: Optional[str] = None
    to_stage: str
    transition_count: int
    unique_journeys: int
    transition_percentage: float
    average_time_to_transition_days: Optional[float] = None
    median_time_to_transition_days: Optional[float] = None
    is_forward: bool
    is_regression: bool
    is_reentry: bool
    is_terminal: bool


class TransitionSummaryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    total_transitions: int
    forward_transition_count: int
    regression_transition_count: int
    same_stage_reentry_count: int
    terminal_transition_count: int
    by_transition: List[TransitionPairDTO] = Field(default_factory=list)


class FunnelStageDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage: str
    sequence: int
    entered_count: int
    advanced_count: int
    regressed_count: int
    exited_count: int
    remaining_count: int
    historical_completion_rate: Optional[float] = None


class JourneyFunnelDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    funnel_stages: List[str]
    stage_metrics: List[FunnelStageDTO]
    total_entered: int
    total_completed: int
    overall_completion_rate: Optional[float] = None
    has_regressions: bool
    has_skip_patterns: bool


class JourneyDurationDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    total_sample_size: int
    average_duration_days: Optional[float] = None
    median_duration_days: Optional[float] = None
    minimum_duration_days: Optional[float] = None
    maximum_duration_days: Optional[float] = None
    p25_duration_days: Optional[float] = None
    p75_duration_days: Optional[float] = None
    active_average_days: Optional[float] = None
    completed_average_days: Optional[float] = None
    cancelled_average_days: Optional[float] = None


class StageResidencyAnalyticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage: str
    sample_size: int
    average_duration_days: Optional[float] = None
    median_duration_days: Optional[float] = None
    p25_days: Optional[float] = None
    p75_days: Optional[float] = None
    minimum_days: Optional[float] = None
    maximum_days: Optional[float] = None
    reentry_rate: float
    oscillation_rate: float
    current_residency_count: int
    residency_category: str


class MaturityAnalyticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    sample_size: int
    average_maturity_score: Optional[float] = None
    median_maturity_score: Optional[float] = None
    lowest_maturity_score: Optional[float] = None
    highest_maturity_score: Optional[float] = None
    maturity_level_counts: Dict[str, int] = Field(default_factory=dict)
    maturity_level_percentages: Dict[str, float] = Field(default_factory=dict)
    lowest_maturity_bucket: Optional[str] = None
    highest_maturity_bucket: Optional[str] = None


class MomentumAnalyticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    sample_size: int
    state_counts: Dict[str, int] = Field(default_factory=dict)
    state_percentages: Dict[str, float] = Field(default_factory=dict)
    advancing_percentage: float
    stable_percentage: float
    weakening_percentage: float
    regressing_percentage: float
    inactive_percentage: float
    unknown_percentage: float


class StabilityAnalyticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    sample_size: int
    level_counts: Dict[str, int] = Field(default_factory=dict)
    level_percentages: Dict[str, float] = Field(default_factory=dict)
    average_stability_score: Optional[float] = None
    reentry_frequency: float
    oscillation_frequency: float
    conflicting_evidence_frequency: float


class VelocityAnalyticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    sample_size: int
    state_counts: Dict[str, int] = Field(default_factory=dict)
    state_percentages: Dict[str, float] = Field(default_factory=dict)
    average_transitions_per_day: Optional[float] = None
    average_transitions_per_week: Optional[float] = None
    average_stage_duration_days: Optional[float] = None


class HealthAnalyticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    sample_size: int
    health_distribution: Dict[str, int] = Field(default_factory=dict)
    health_percentages: Dict[str, float] = Field(default_factory=dict)
    healthy_percentage: float
    stalled_percentage: float
    regressing_percentage: float
    inactive_percentage: float
    insufficient_data_percentage: float


class ProgressionPatternDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    sample_size: int
    average_forward_transitions: Optional[float] = None
    average_regressions: Optional[float] = None
    average_reentries: Optional[float] = None
    average_stage_changes: Optional[float] = None
    average_journey_age_days: Optional[float] = None
    progression_consistency_score: Optional[float] = None
    pattern_distribution: Dict[str, int] = Field(default_factory=dict)
    pattern_percentages: Dict[str, float] = Field(default_factory=dict)


class ObservedStageOutcomeDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage: str
    outcome: str
    success_count: int
    failure_count: int
    sample_size: int
    observed_rate: Optional[float] = None
    observation_window_days: int
    minimum_sample_met: bool
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    confidence_level: float
    calculation_method: str
    limitations: List[str] = Field(default_factory=list)
    data_status: str


class TrendPointDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp: datetime
    period_label: str
    metric: str
    value: float
    sample_size: int


class TrendAnalyticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    granularity: str
    metrics: List[str]
    data_points: List[TrendPointDTO]
    total_periods: int


class AnalyticsDiagnosticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    total_execution_time_ms: float
    journeys_processed: int
    transitions_processed: int
    maturity_results_processed: int
    metrics_calculated: List[str]
    warnings: List[str]
    validation_errors: List[str]
    empty_dataset: bool
    partial_dataset: bool
    insufficient_data_metrics: List[str]


class AnalyticsProvenanceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    analytics_id: str
    workspace_id: str
    generated_at: datetime
    engine_version: str
    pipeline_version: str
    configuration_version: str
    source_journey_count: int
    source_transition_count: int
    source_maturity_count: int
    calculation_methods: List[str]
    statistical_methods: List[str]


class JourneyAnalyticsResultDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    analytics_id: str
    workspace_id: str
    journey_type: Optional[str] = None
    definition_version: Optional[str] = None
    observation_window: AnalyticsObservationWindowDTO
    generated_at: datetime
    journey_count: int
    distribution: JourneyDistributionDTO
    stage_analytics: Dict[str, StageAnalyticsDTO] = Field(default_factory=dict)
    transition_metrics: TransitionSummaryDTO
    funnel: Optional[JourneyFunnelDTO] = None
    duration_metrics: JourneyDurationDTO
    residency_analytics: Dict[str, StageResidencyAnalyticsDTO] = Field(default_factory=dict)
    maturity_analytics: MaturityAnalyticsDTO
    momentum_analytics: MomentumAnalyticsDTO
    stability_analytics: StabilityAnalyticsDTO
    velocity_analytics: VelocityAnalyticsDTO
    health_analytics: HealthAnalyticsDTO
    progression_patterns: ProgressionPatternDTO
    outcome_analytics: Dict[str, ObservedStageOutcomeDTO] = Field(default_factory=dict)
    trend_analytics: Optional[TrendAnalyticsDTO] = None
    diagnostics: AnalyticsDiagnosticsDTO
    provenance: AnalyticsProvenanceDTO


# Analytics request models
class CalculateAnalyticsRequest(BaseModel):
    workspace_id: str
    journey_type: Optional[str] = None
    definition_version: Optional[str] = None
    configuration_version: Optional[str] = None
    observation_window_days: Optional[int] = None
    use_cache: bool = True


class CohortAnalyticsRequest(BaseModel):
    workspace_id: str
    cohort_name: str
    journey_type: Optional[str] = None
    stage: Optional[str] = None
    journey_status: Optional[str] = None
    observation_window_days: int = 365
    custom_filters: Dict[str, Any] = Field(default_factory=dict)
