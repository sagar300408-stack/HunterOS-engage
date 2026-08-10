from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

class AnalyticsScope(str, enum.Enum):
    WORKSPACE = "WORKSPACE"
    JOURNEY_TYPE = "JOURNEY_TYPE"
    JOURNEY_DEFINITION = "JOURNEY_DEFINITION"
    STAGE = "STAGE"
    TIME_WINDOW = "TIME_WINDOW"
    COHORT = "COHORT"
    CUSTOM = "CUSTOM"

class ResidencyCategory(str, enum.Enum):
    FAST_RESIDENCY = "FAST_RESIDENCY"
    NORMAL_RESIDENCY = "NORMAL_RESIDENCY"
    SLOW_RESIDENCY = "SLOW_RESIDENCY"
    EXTENDED_RESIDENCY = "EXTENDED_RESIDENCY"
    UNKNOWN = "UNKNOWN"

class ProgressionPattern(str, enum.Enum):
    STEADY_PROGRESS = "STEADY_PROGRESS"
    MULTI_STEP_PROGRESS = "MULTI_STEP_PROGRESS"
    OSCILLATING = "OSCILLATING"
    REGRESSIVE = "REGRESSIVE"
    STALLED = "STALLED"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"

class TrendGranularity(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"

class OutcomeDataStatus(str, enum.Enum):
    CALCULATED = "CALCULATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class AnalyticsObservationWindow:
    start_at: datetime
    end_at: datetime
    timezone: str = "UTC"
    
    @property
    def duration_days(self) -> float:
        delta = self.end_at - self.start_at
        return max(0.0, delta.total_seconds() / 86400.0)

@dataclass(frozen=True)
class JourneyDistributionMetrics:
    total_journeys: int
    active_journeys: int
    completed_journeys: int
    cancelled_journeys: int
    inactive_journeys: int
    archived_journeys: int  # alias for LOST
    by_journey_type: Dict[str, Dict[str, Any]]
    by_status: Dict[str, Dict[str, Any]]
    by_current_stage: Dict[str, Dict[str, Any]]
    by_maturity_level: Dict[str, Dict[str, Any]]
    by_momentum_state: Dict[str, Dict[str, Any]]
    by_stability_level: Dict[str, Dict[str, Any]]
    by_velocity_state: Dict[str, Dict[str, Any]]
    by_health_state: Dict[str, Dict[str, Any]]

@dataclass(frozen=True)
class StageAnalytics:
    stage: str
    journey_count: int
    percentage_of_journeys: float
    unique_entries: int
    unique_exits: int
    current_residency_count: int
    completed_residency_count: int
    average_residency_days: Optional[float]
    median_residency_days: Optional[float]
    minimum_residency_days: Optional[float]
    maximum_residency_days: Optional[float]
    p25_residency_days: Optional[float]
    p75_residency_days: Optional[float]

@dataclass(frozen=True)
class TransitionAnalytics:
    from_stage: Optional[str]
    to_stage: str
    transition_count: int
    unique_journeys: int
    transition_percentage: float
    average_time_to_transition_days: Optional[float]
    median_time_to_transition_days: Optional[float]
    is_forward: bool
    is_regression: bool
    is_reentry: bool
    is_terminal: bool

@dataclass(frozen=True)
class TransitionSummaryMetrics:
    total_transitions: int
    forward_transition_count: int
    regression_transition_count: int
    same_stage_reentry_count: int
    terminal_transition_count: int
    by_transition: List[TransitionAnalytics]

@dataclass(frozen=True)
class JourneyFunnelStageMetrics:
    stage: str
    sequence: int
    entered_count: int
    advanced_count: int
    regressed_count: int
    exited_count: int
    remaining_count: int
    historical_completion_rate: Optional[float]

@dataclass(frozen=True)
class JourneyFunnelMetrics:
    funnel_stages: List[str]
    stage_metrics: List[JourneyFunnelStageMetrics]
    total_entered: int
    total_completed: int
    overall_completion_rate: Optional[float]
    has_regressions: bool
    has_skip_patterns: bool

@dataclass(frozen=True)
class JourneyDurationMetrics:
    total_sample_size: int
    average_duration_days: Optional[float]
    median_duration_days: Optional[float]
    minimum_duration_days: Optional[float]
    maximum_duration_days: Optional[float]
    p25_duration_days: Optional[float]
    p75_duration_days: Optional[float]
    active_average_days: Optional[float]
    completed_average_days: Optional[float]
    cancelled_average_days: Optional[float]

@dataclass(frozen=True)
class StageResidencyAnalytics:
    stage: str
    sample_size: int
    average_duration_days: Optional[float]
    median_duration_days: Optional[float]
    p25_days: Optional[float]
    p75_days: Optional[float]
    minimum_days: Optional[float]
    maximum_days: Optional[float]
    reentry_rate: float
    oscillation_rate: float
    current_residency_count: int
    residency_category: ResidencyCategory

@dataclass(frozen=True)
class MaturityAnalytics:
    sample_size: int
    average_maturity_score: Optional[float]
    median_maturity_score: Optional[float]
    lowest_maturity_score: Optional[float]
    highest_maturity_score: Optional[float]
    maturity_level_counts: Dict[str, int]
    maturity_level_percentages: Dict[str, float]
    lowest_maturity_bucket: Optional[str]
    highest_maturity_bucket: Optional[str]

@dataclass(frozen=True)
class MomentumAnalytics:
    sample_size: int
    state_counts: Dict[str, int]
    state_percentages: Dict[str, float]
    advancing_percentage: float
    stable_percentage: float
    weakening_percentage: float
    regressing_percentage: float
    inactive_percentage: float
    unknown_percentage: float

@dataclass(frozen=True)
class StabilityAnalytics:
    sample_size: int
    level_counts: Dict[str, int]
    level_percentages: Dict[str, float]
    average_stability_score: Optional[float]
    reentry_frequency: float
    oscillation_frequency: float
    conflicting_evidence_frequency: float

@dataclass(frozen=True)
class VelocityAnalytics:
    sample_size: int
    state_counts: Dict[str, int]
    state_percentages: Dict[str, float]
    average_transitions_per_day: Optional[float]
    average_transitions_per_week: Optional[float]
    average_stage_duration_days: Optional[float]

@dataclass(frozen=True)
class JourneyHealthAnalytics:
    sample_size: int
    health_distribution: Dict[str, int]
    health_percentages: Dict[str, float]
    healthy_percentage: float
    stalled_percentage: float
    regressing_percentage: float
    inactive_percentage: float
    insufficient_data_percentage: float

@dataclass(frozen=True)
class ProgressionPatternAnalytics:
    sample_size: int
    average_forward_transitions: Optional[float]
    average_regressions: Optional[float]
    average_reentries: Optional[float]
    average_stage_changes: Optional[float]
    average_journey_age_days: Optional[float]
    progression_consistency_score: Optional[float]
    pattern_distribution: Dict[str, int]
    pattern_percentages: Dict[str, float]

@dataclass(frozen=True)
class ObservedStageOutcomeAnalytics:
    stage: str
    outcome: str
    success_count: int
    failure_count: int
    sample_size: int
    observed_rate: Optional[float]
    observation_window_days: int
    minimum_sample_met: bool
    confidence_interval_lower: Optional[float]
    confidence_interval_upper: Optional[float]
    confidence_level: float
    calculation_method: str
    limitations: List[str]
    data_status: OutcomeDataStatus

@dataclass(frozen=True)
class JourneyTrendPoint:
    timestamp: datetime
    period_label: str
    metric: str
    value: float
    sample_size: int

@dataclass(frozen=True)
class JourneyTrendAnalytics:
    granularity: TrendGranularity
    observation_window: AnalyticsObservationWindow
    metrics: List[str]
    data_points: List[JourneyTrendPoint]
    total_periods: int

@dataclass(frozen=True)
class JourneyCohortDefinition:
    cohort_id: uuid.UUID
    cohort_name: str
    workspace_id: Union[uuid.UUID, str]
    journey_type: Optional[str] = None
    journey_definition_id: Optional[str] = None
    stage: Optional[str] = None
    journey_status: Optional[str] = None
    maturity_level: Optional[str] = None
    momentum_state: Optional[str] = None
    stability_level: Optional[str] = None
    velocity_state: Optional[str] = None
    health_state: Optional[str] = None
    time_window: Optional[AnalyticsObservationWindow] = None
    custom_filters: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class JourneyCohortMetrics:
    cohort: JourneyCohortDefinition
    journey_count: int
    average_duration_days: Optional[float]
    median_duration_days: Optional[float]
    average_maturity_score: Optional[float]
    stage_distribution: Dict[str, int]
    momentum_distribution: Dict[str, int]
    stability_distribution: Dict[str, int]
    health_distribution: Dict[str, int]
    transition_rate: Optional[float]
    historical_outcome_rate: Optional[float]

@dataclass(frozen=True)
class JourneyCohortComparison:
    comparison_id: uuid.UUID
    workspace_id: Union[uuid.UUID, str]
    cohort_metrics: List[JourneyCohortMetrics]
    generated_at: datetime
    observation_window: AnalyticsObservationWindow
    comparison_notes: List[str]

@dataclass(frozen=True)
class JourneyAnalyticsDiagnostics:
    stage_timings: Dict[str, float]
    total_execution_time_ms: float
    journeys_processed: int
    transitions_processed: int
    timeline_events_processed: int
    maturity_results_processed: int
    metrics_calculated: List[str]
    warnings: List[str]
    validation_errors: List[str]
    empty_dataset: bool
    partial_dataset: bool
    insufficient_data_metrics: List[str]

@dataclass(frozen=True)
class JourneyAnalyticsProvenance:
    analytics_id: uuid.UUID
    workspace_id: Union[uuid.UUID, str]
    generated_at: datetime
    observation_window: AnalyticsObservationWindow
    engine_version: str
    pipeline_version: str
    configuration_version: str
    source_journey_count: int
    source_transition_count: int
    source_maturity_count: int
    filters: Dict[str, Any]
    cohort_definition: Optional[Dict[str, Any]]
    calculation_methods: List[str]
    statistical_methods: List[str]

@dataclass(frozen=True)
class JourneyAnalyticsResult:
    analytics_id: uuid.UUID
    workspace_id: Union[uuid.UUID, str]
    journey_type: Optional[str]
    definition_version: Optional[str]
    observation_window: AnalyticsObservationWindow
    generated_at: datetime
    journey_count: int
    distribution: JourneyDistributionMetrics
    stage_analytics: Dict[str, StageAnalytics]
    transition_metrics: TransitionSummaryMetrics
    funnel: Optional[JourneyFunnelMetrics]
    duration_metrics: JourneyDurationMetrics
    residency_analytics: Dict[str, StageResidencyAnalytics]
    maturity_analytics: MaturityAnalytics
    momentum_analytics: MomentumAnalytics
    stability_analytics: StabilityAnalytics
    velocity_analytics: VelocityAnalytics
    health_analytics: JourneyHealthAnalytics
    progression_patterns: ProgressionPatternAnalytics
    outcome_analytics: Dict[str, ObservedStageOutcomeAnalytics]
    trend_analytics: Optional[JourneyTrendAnalytics]
    cohort_metrics: Optional[JourneyCohortMetrics]
    diagnostics: JourneyAnalyticsDiagnostics
    provenance: JourneyAnalyticsProvenance
