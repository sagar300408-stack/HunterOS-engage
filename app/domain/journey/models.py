"""
HunterOS Engage V1 — Customer Journey Intelligence Domain Models
Phase 2.4.1: Journey Foundation + Phase 2.4.2: Stage Progression Engine

Core domain entities for representing customer business journeys.
All models are frozen dataclasses for immutability.

Architectural Invariants:
1. Strictly descriptive — describes observed journey state, never predicts.
2. Evidence-backed transitions only.
3. Append-only timeline; historical transitions are immutable.
4. Workspace-isolated; cross-workspace evidence is rejected.
"""

from __future__ import annotations

import enum
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union


# ── 1. Enumerations ─────────────────────────────────────────────────────────────


class JourneyType(str, enum.Enum):
    """Business journey type. Extensible across industries."""
    SALES = "SALES"
    PROPERTY_PURCHASE = "PROPERTY_PURCHASE"
    PROPERTY_RENTAL = "PROPERTY_RENTAL"
    SERVICE = "SERVICE"
    SUPPORT = "SUPPORT"
    HEALTHCARE = "HEALTHCARE"
    PARTNERSHIP = "PARTNERSHIP"
    CUSTOM = "CUSTOM"


class JourneyStageCode(str, enum.Enum):
    """
    Standard cross-industry stage codes.
    Journey definitions may use any subset of these,
    plus industry-specific codes via CUSTOM.
    """
    # Cross-industry stages
    NEW_LEAD = "NEW_LEAD"
    INTERESTED = "INTERESTED"
    QUALIFIED = "QUALIFIED"
    ENGAGED = "ENGAGED"
    MEETING_SCHEDULED = "MEETING_SCHEDULED"
    MEETING_COMPLETED = "MEETING_COMPLETED"
    PROPOSAL = "PROPOSAL"
    NEGOTIATION = "NEGOTIATION"
    BOOKING = "BOOKING"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"
    INACTIVE = "INACTIVE"

    # Real Estate specific
    SITE_VISIT_SCHEDULED = "SITE_VISIT_SCHEDULED"
    SITE_VISIT_COMPLETED = "SITE_VISIT_COMPLETED"
    PROPERTY_SHORTLISTED = "PROPERTY_SHORTLISTED"

    # Healthcare specific
    CONSULTATION_SCHEDULED = "CONSULTATION_SCHEDULED"
    CONSULTATION_COMPLETED = "CONSULTATION_COMPLETED"
    TREATMENT_PLAN = "TREATMENT_PLAN"

    # Extensibility
    CUSTOM = "CUSTOM"


class JourneyStatus(str, enum.Enum):
    """Journey lifecycle status. Distinct from stage (position)."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    LOST = "LOST"
    INACTIVE = "INACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class TransitionType(str, enum.Enum):
    """Type of stage transition observed."""
    ADVANCE = "ADVANCE"
    REGRESSION = "REGRESSION"
    LATERAL = "LATERAL"
    REACTIVATION = "REACTIVATION"
    INITIALIZATION = "INITIALIZATION"
    COMPLETION = "COMPLETION"
    CLOSURE = "CLOSURE"
    CUSTOM = "CUSTOM"


class EvidenceType(str, enum.Enum):
    """Source type of journey evidence."""
    CONVERSATION = "CONVERSATION"
    MESSAGE = "MESSAGE"
    TIMELINE_EVENT = "TIMELINE_EVENT"
    INTENT = "INTENT"
    INTENT_EVOLUTION = "INTENT_EVOLUTION"
    INTENT_RESOLUTION = "INTENT_RESOLUTION"
    MEMORY_CONTEXT = "MEMORY_CONTEXT"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


class TimelineEventType(str, enum.Enum):
    """Type of journey timeline event."""
    JOURNEY_STARTED = "JOURNEY_STARTED"
    STAGE_ENTERED = "STAGE_ENTERED"
    STAGE_ADVANCED = "STAGE_ADVANCED"
    STAGE_REGRESSED = "STAGE_REGRESSED"
    STAGE_REACTIVATED = "STAGE_REACTIVATED"
    STAGE_COMPLETED = "STAGE_COMPLETED"
    JOURNEY_CLOSED = "JOURNEY_CLOSED"
    JOURNEY_REOPENED = "JOURNEY_REOPENED"
    NO_CHANGE_OBSERVATION = "NO_CHANGE_OBSERVATION"


# ── 2. Value Objects ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class JourneyEvidence:
    """A single piece of evidence supporting a stage or transition."""
    evidence_id: uuid.UUID = field(default_factory=uuid.uuid4)
    evidence_type: EvidenceType = EvidenceType.SYSTEM
    source_id: str = ""
    source_module: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfidenceFactors:
    """Deterministic confidence factor breakdown."""
    intent_match: float = 0.0
    timeline_match: float = 0.0
    conversation_match: float = 0.0
    rule_strength: float = 0.0
    evidence_count_factor: float = 0.0
    evidence_quality_factor: float = 0.0
    source_consistency_factor: float = 0.0
    recency_factor: float = 0.0

    def compute_aggregate(self) -> float:
        """Deterministic weighted average of all factors."""
        factors = [
            (self.intent_match, 0.25),
            (self.timeline_match, 0.15),
            (self.conversation_match, 0.15),
            (self.rule_strength, 0.20),
            (self.evidence_count_factor, 0.08),
            (self.evidence_quality_factor, 0.07),
            (self.source_consistency_factor, 0.05),
            (self.recency_factor, 0.05),
        ]
        active = [(v, w) for v, w in factors if v > 0.0]
        if not active:
            return 0.0
        total_weight = sum(w for _, w in active)
        if total_weight == 0.0:
            return 0.0
        return min(1.0, max(0.0, sum(v * w for v, w in active) / total_weight))


@dataclass(frozen=True)
class JourneyProvenance:
    """Full traceability for journey results."""
    journey_version: str = "2.4.2"
    definition_version: str = "1.0.0"
    progression_engine_version: str = "2.4.2"
    rule_pack_version: str = "1.0.0"
    pipeline_version: str = "1.0.0"
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_modules: List[str] = field(default_factory=list)
    source_artifacts: List[str] = field(default_factory=list)
    workspace_id: Optional[Union[uuid.UUID, str]] = None


@dataclass(frozen=True)
class JourneyMetadata:
    """Extensible metadata container for journey entities."""
    tags: Dict[str, str] = field(default_factory=dict)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True)
class JourneyDiagnostics:
    """Structured diagnostics for observability."""
    pipeline_version: str = "1.0.0"
    stage_timings: Dict[str, float] = field(default_factory=dict)
    rules_evaluated: int = 0
    rules_matched: int = 0
    candidate_transition_count: int = 0
    accepted_transition_count: int = 0
    rejected_transition_count: int = 0
    evidence_count: int = 0
    validation_errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    correlation_id: str = ""
    causation_id: str = ""


# ── 3. Stage Definition ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StageDefinition:
    """
    Defines a stage within a journey.
    Immutable once registered for runtime execution.
    """
    stage_id: uuid.UUID = field(default_factory=uuid.uuid4)
    stage_code: JourneyStageCode = JourneyStageCode.CUSTOM
    name: str = ""
    description: str = ""
    journey_type: JourneyType = JourneyType.SALES
    sequence: int = 0
    allowed_previous_stages: List[JourneyStageCode] = field(default_factory=list)
    allowed_next_stages: List[JourneyStageCode] = field(default_factory=list)
    is_terminal: bool = False
    is_entry_stage: bool = False
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"


# ── 4. Journey Definition ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class JourneyDefinition:
    """
    Defines the allowed structure of a business journey.
    Contains the set of stages and their valid transitions.
    """
    journey_id: uuid.UUID = field(default_factory=uuid.uuid4)
    journey_type: JourneyType = JourneyType.SALES
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    stage_definitions: List[StageDefinition] = field(default_factory=list)
    stage_ids: List[uuid.UUID] = field(default_factory=list)
    entry_stage: JourneyStageCode = JourneyStageCode.NEW_LEAD
    terminal_stages: List[JourneyStageCode] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def stages(self) -> List[StageDefinition]:
        """Alias for stage_definitions."""
        return self.stage_definitions

    def get_stage_definition(self, stage_code: JourneyStageCode) -> Optional[StageDefinition]:
        """Look up a StageDefinition by code."""
        for sd in self.stage_definitions:
            if sd.stage_code == stage_code:
                return sd
        return None

    def get_stage_sequence(self) -> List[JourneyStageCode]:
        """Return stages sorted by sequence order."""
        sorted_stages = sorted(self.stage_definitions, key=lambda s: s.sequence)
        return [s.stage_code for s in sorted_stages]

    def is_valid_transition(self, from_stage: JourneyStageCode, to_stage: JourneyStageCode) -> bool:
        """Check if a transition is allowed by this definition."""
        from_def = self.get_stage_definition(from_stage)
        if from_def is None:
            return False
        if from_def.is_terminal:
            return False
        return to_stage in from_def.allowed_next_stages


# ── 5. Stage Transition ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class JourneyStageTransition:
    """Records a single stage transition with full evidence."""
    transition_id: uuid.UUID = field(default_factory=uuid.uuid4)
    journey_instance_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[Union[uuid.UUID, str]] = None
    from_stage: Optional[JourneyStageCode] = None
    to_stage: JourneyStageCode = JourneyStageCode.NEW_LEAD
    transition_type: TransitionType = TransitionType.INITIALIZATION
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: List[JourneyEvidence] = field(default_factory=list)
    source_modules: List[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_factors: ConfidenceFactors = field(default_factory=ConfidenceFactors)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Optional[JourneyProvenance] = None


# ── 6. Journey Timeline Event ────────────────────────────────────────────────────


@dataclass(frozen=True)
class JourneyTimelineEvent:
    """Append-only timeline event. Historical events are never rewritten."""
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    journey_instance_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[Union[uuid.UUID, str]] = None
    event_type: TimelineEventType = TimelineEventType.NO_CHANGE_OBSERVATION
    stage: Optional[JourneyStageCode] = None
    previous_stage: Optional[JourneyStageCode] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: List[JourneyEvidence] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── 7. Journey Timeline ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class JourneyTimeline:
    """Chronological append-only record of all journey events."""
    timeline_id: uuid.UUID = field(default_factory=uuid.uuid4)
    journey_instance_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[Union[uuid.UUID, str]] = None
    events: List[JourneyTimelineEvent] = field(default_factory=list)


# ── 8. Journey State ─────────────────────────────────────────────────────────────


@dataclass
class JourneyState:
    """
    Runtime state of a customer's journey instance.
    This is the ONLY mutable entity — it represents current journey position.
    """
    journey_instance_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[Union[uuid.UUID, str]] = None
    entity_type: str = "CUSTOMER"
    entity_id: str = ""
    journey_definition_id: uuid.UUID = field(default_factory=uuid.uuid4)
    journey_definition_version: str = "1.0.0"
    current_stage: JourneyStageCode = JourneyStageCode.NEW_LEAD
    previous_stage: Optional[JourneyStageCode] = None
    stage_entered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    journey_started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_transition_at: Optional[datetime] = None
    status: JourneyStatus = JourneyStatus.ACTIVE
    stage_history: List[JourneyStageCode] = field(default_factory=list)
    transitions: List[JourneyStageTransition] = field(default_factory=list)
    timeline: JourneyTimeline = field(default_factory=JourneyTimeline)
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Optional[JourneyProvenance] = None

    def compute_progression_fingerprint(self, evidence_ids: List[str], definition_version: str) -> str:
        """
        Deterministic fingerprint for idempotency protection.
        Same inputs → same fingerprint → no duplicate transitions.
        """
        parts = [
            str(self.workspace_id or ""),
            self.entity_type,
            self.entity_id,
            self.current_stage.value,
            definition_version,
        ] + sorted(evidence_ids)
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()


# ── 9. Transition Candidate ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class TransitionCandidate:
    """A candidate transition proposed by a progression rule."""
    from_stage: JourneyStageCode = JourneyStageCode.NEW_LEAD
    to_stage: JourneyStageCode = JourneyStageCode.INTERESTED
    transition_type: TransitionType = TransitionType.ADVANCE
    evidence: List[JourneyEvidence] = field(default_factory=list)
    confidence: float = 0.0
    confidence_factors: ConfidenceFactors = field(default_factory=ConfidenceFactors)
    rule_name: str = ""
    reason: str = ""
    source_modules: List[str] = field(default_factory=list)


# ── 10. Journey Progression Result ───────────────────────────────────────────────


@dataclass(frozen=True)
class JourneyProgressionResult:
    """Final output of the progression pipeline."""
    progression_id: uuid.UUID = field(default_factory=uuid.uuid4)
    journey_instance_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: Optional[Union[uuid.UUID, str]] = None
    entity_type: str = "CUSTOMER"
    entity_id: str = ""
    previous_stage: Optional[JourneyStageCode] = None
    current_stage: JourneyStageCode = JourneyStageCode.NEW_LEAD
    new_stage: Optional[JourneyStageCode] = None
    transition: Optional[JourneyStageTransition] = None
    transition_type: Optional[TransitionType] = None
    timeline_event: Optional[JourneyTimelineEvent] = None
    did_progress: bool = False
    confidence: float = 0.0
    confidence_factors: Optional[ConfidenceFactors] = None
    evidence: List[JourneyEvidence] = field(default_factory=list)
    accepted_candidate: Optional[TransitionCandidate] = None
    rejected_candidates: List[TransitionCandidate] = field(default_factory=list)
    diagnostics: JourneyDiagnostics = field(default_factory=JourneyDiagnostics)
    provenance: JourneyProvenance = field(default_factory=JourneyProvenance)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    idempotency_fingerprint: str = ""
    new_state: Optional[Any] = None

    @property
    def transition_occurred(self) -> bool:
        return self.did_progress
