"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Journey Maturity & Observed Probability Models

Immutable domain models, enums, value objects, and diagnostics for descriptive
journey maturity, momentum, stability, residency, velocity, observed probability,
and health.

CRITICAL INVARIANTS:
1. Descriptive & Evidence-Based ONLY: No predictive AI, ML models, or next-best-action recommendations.
2. Immutability: All state representations are frozen value objects.
3. No small-sample fiction: If historical outcomes < min_sample, observed_probability is None.
4. Strict multi-tenancy: Workspace boundaries are preserved in all data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.journey.models import (
    JourneyStageCode,
    JourneyStatus,
    JourneyType,
)


# ── Enumerations ─────────────────────────────────────────────────────────────


class JourneyMaturityLevel(str, Enum):
    """Configurable progression maturity levels."""
    INITIAL = "INITIAL"
    EARLY = "EARLY"
    DEVELOPING = "DEVELOPING"
    QUALIFIED = "QUALIFIED"
    ADVANCED = "ADVANCED"
    LATE_STAGE = "LATE_STAGE"
    COMPLETED = "COMPLETED"


class JourneyMomentumState(str, Enum):
    """Descriptive recent direction of observed stage movement."""
    STRONGLY_ADVANCING = "STRONGLY_ADVANCING"
    ADVANCING = "ADVANCING"
    STABLE = "STABLE"
    WEAKENING = "WEAKENING"
    REGRESSING = "REGRESSING"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


class JourneyStabilityLevel(str, Enum):
    """Descriptive stability level based on repeated evidence and historical transitions."""
    VERY_STABLE = "VERY_STABLE"
    STABLE = "STABLE"
    MODERATE = "MODERATE"
    UNSTABLE = "UNSTABLE"
    HIGHLY_UNSTABLE = "HIGHLY_UNSTABLE"
    UNKNOWN = "UNKNOWN"


class StageResidencyStatus(str, Enum):
    """Status of an individual stage residency interval."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class StageVelocityState(str, Enum):
    """Descriptive historical stage velocity."""
    FAST = "FAST"
    NORMAL = "NORMAL"
    SLOW = "SLOW"
    STALLED = "STALLED"
    UNKNOWN = "UNKNOWN"


class ObservedProbabilityType(str, Enum):
    """Explicitly labeled probability classification."""
    HISTORICAL_OBSERVED = "HISTORICAL_OBSERVED"


class ObservedProbabilityStatus(str, Enum):
    """Status of historical observed probability calculation."""
    CALCULATED = "CALCULATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class JourneyHealthState(str, Enum):
    """Descriptive structural health state of a customer journey."""
    HEALTHY_PROGRESSING = "HEALTHY_PROGRESSING"
    HEALTHY_STABLE = "HEALTHY_STABLE"
    SLOW_PROGRESSING = "SLOW_PROGRESSING"
    STALLED = "STALLED"
    REGRESSING = "REGRESSING"
    INACTIVE = "INACTIVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


# ── Value Objects & Provenance ───────────────────────────────────────────────


@dataclass(frozen=True)
class JourneyMaturityProvenance:
    """Audit trail and provenance for a journey maturity calculation."""
    calculation_id: uuid.UUID
    journey_id: uuid.UUID
    workspace_id: uuid.UUID
    entity_id: str
    engine_version: str
    pipeline_version: str
    configuration_version: str
    generated_at: datetime
    source_modules: List[str]
    source_artifacts: List[str]
    calculation_method: str
    correlation_id: Optional[str] = None


@dataclass(frozen=True)
class MaturityFactors:
    """Detailed constituent factors contributing to journey maturity score (each 0.0 - 1.0)."""
    stage_position_factor: float = 0.0
    stage_completion_factor: float = 0.0
    transition_history_factor: float = 0.0
    evidence_strength_factor: float = 0.0
    journey_age_factor: float = 0.0
    stage_stability_factor: float = 0.0
    progression_consistency_factor: float = 0.0
    custom_factors: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class JourneyMaturity:
    """
    Descriptive maturity of a customer's progression through their journey definition.
    Score: 0.0 to 1.0.
    """
    maturity_score: float
    maturity_level: JourneyMaturityLevel
    current_stage: JourneyStageCode
    stage_position: int
    total_active_stages: int
    completed_stage_count: int
    journey_progress_ratio: float
    stage_duration_days: float
    journey_age_days: float
    evidence_strength: float
    calculated_at: datetime
    factors: MaturityFactors
    provenance: JourneyMaturityProvenance


@dataclass(frozen=True)
class JourneyMomentum:
    """
    Descriptive measure of the recent direction of observed stage movement.
    Derived purely from observed historical transitions.
    """
    state: JourneyMomentumState
    momentum_score: float  # -1.0 (strongly regressing) to +1.0 (strongly advancing)
    recent_advancements_count: int
    recent_regressions_count: int
    days_since_last_transition: float
    transition_frequency_per_week: float
    description: str
    calculated_at: datetime


@dataclass(frozen=True)
class JourneyStability:
    """
    Descriptive stability evaluation of the current journey state.
    Evaluates stage residency, oscillation/re-entry, and signal consistency.
    """
    stability_score: float  # 0.0 (highly unstable) to 1.0 (very stable)
    stability_level: JourneyStabilityLevel
    current_stage_duration_days: float
    stage_reentry_count: int
    stage_transition_count: int
    supporting_evidence_count: int
    conflicting_evidence_count: int
    calculated_at: datetime
    factors: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class StageResidency:
    """
    Immutable record of time spent within a specific journey stage.
    Once closed (exited_at set), the residency interval is permanently immutable.
    """
    residency_id: uuid.UUID
    stage: JourneyStageCode
    entered_at: datetime
    exited_at: Optional[datetime]
    duration_days: float
    transition_count: int
    reentry_count: int
    evidence_count: int
    confidence: float
    status: StageResidencyStatus


@dataclass(frozen=True)
class StageVelocity:
    """
    Descriptive historical stage velocity and transition frequency.
    """
    transitions_per_day: float
    transitions_per_week: float
    average_stage_duration_days: float
    current_stage_duration_days: float
    historical_average_duration_days: Optional[float]
    velocity_state: StageVelocityState
    calculated_at: datetime


@dataclass(frozen=True)
class ObservedJourneyProbability:
    """
    Statistical evidence-derived historical likelihood based only on explicitly
    available journey outcome records in the same workspace.
    
    NEVER fabricated, guessed, or derived from ML/LLM predictions.
    If sample_size < minimum_required_sample, value is None with status INSUFFICIENT_DATA.
    """
    probability_id: uuid.UUID
    value: Optional[float]
    status: ObservedProbabilityStatus
    probability_type: ObservedProbabilityType = ObservedProbabilityType.HISTORICAL_OBSERVED
    target_stage: Optional[JourneyStageCode] = None
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
    cohort_filters: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    provenance: Optional[JourneyMaturityProvenance] = None
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Alias for backward compatibility & direct import convenience
ObservedProbability = ObservedJourneyProbability


@dataclass(frozen=True)
class JourneyHealth:
    """Descriptive structural health summary of the journey."""
    state: JourneyHealthState
    summary: str
    factors: Dict[str, Any] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class JourneyMaturityDiagnostics:
    """Operational and performance diagnostics for maturity pipeline execution."""
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


@dataclass(frozen=True)
class JourneyMaturityResult:
    """
    Unified immutable result artifact containing all calculated descriptive maturity,
    momentum, stability, velocity, residency, health, and observed probability metrics.
    """
    journey_id: uuid.UUID
    workspace_id: uuid.UUID
    entity_id: str
    current_stage: JourneyStageCode
    journey_status: JourneyStatus
    maturity: JourneyMaturity
    momentum: JourneyMomentum
    stability: JourneyStability
    velocity: StageVelocity
    stage_residency: List[StageResidency]
    current_residency: StageResidency
    observed_probability: Optional[ObservedJourneyProbability]
    health: JourneyHealth
    diagnostics: JourneyMaturityDiagnostics
    provenance: JourneyMaturityProvenance
    calculated_at: datetime
