"""
HunterOS Engage V1 — Stage Progression Engine
Phase 2.4.2: 8-Stage Deterministic Progression Pipeline

Pipeline Stages:
1. Load Journey State
2. Load Journey Definition
3. Load Intelligence Context
4. Normalize Evidence
5. Generate Candidate Transitions
6. Resolve Transition (conflict resolution)
7. Validate Progression
8. Generate Journey Progression Result

Architectural Invariants:
- Deterministic: same inputs → same outputs
- Descriptive only: observes, never predicts
- Evidence-backed: no transition without evidence
- Idempotent: duplicate evidence → no duplicate transitions
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.exceptions import (
    DuplicateTransitionError,
    InvalidEvidenceError,
    InvalidTransitionError,
    JourneyDefinitionError,
    JourneyNotFoundError,
    StageValidationError,
    TerminalStageError,
    WorkspaceIsolationError,
)
from app.domain.journey.models import (
    ConfidenceFactors,
    EvidenceType,
    JourneyDefinition,
    JourneyDiagnostics,
    JourneyEvidence,
    JourneyProgressionResult,
    JourneyProvenance,
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    JourneyTimeline,
    JourneyTimelineEvent,
    TimelineEventType,
    TransitionCandidate,
    TransitionType,
)
from app.domain.journey.progression.registry import (
    StageProgressionRuleRegistry,
    default_rule_registry,
)


class StageTransitionResolver:
    """
    Resolves conflicts when multiple candidate transitions are proposed.

    Resolution strategy:
    1. Collect all candidate transitions
    2. Validate each against JourneyDefinition
    3. Remove invalid transitions
    4. Compare evidence strength
    5. Resolve mutually exclusive candidates
    6. Select the strongest observed transition
    7. Preserve rejected candidates in diagnostics
    """

    def resolve(
        self,
        candidates: List[TransitionCandidate],
        journey_definition: JourneyDefinition,
        current_stage: JourneyStageCode,
    ) -> Tuple[Optional[TransitionCandidate], List[TransitionCandidate]]:
        """
        Resolve candidate transitions and return (accepted, rejected).

        Returns:
            Tuple of (accepted_candidate_or_None, rejected_candidates_list)
        """
        if not candidates:
            return None, []

        # Step 1: Filter valid transitions against definition
        valid: List[TransitionCandidate] = []
        rejected: List[TransitionCandidate] = []

        for candidate in candidates:
            # Initialization candidates are always valid
            if candidate.transition_type == TransitionType.INITIALIZATION:
                valid.append(candidate)
                continue

            # Check if the transition is allowed by the definition
            if journey_definition.is_valid_transition(candidate.from_stage, candidate.to_stage):
                valid.append(candidate)
            else:
                # Check for reactivation (special case: terminal → non-terminal)
                if candidate.transition_type == TransitionType.REACTIVATION:
                    valid.append(candidate)
                else:
                    rejected.append(candidate)

        if not valid:
            return None, rejected

        # Step 2: Sort by confidence (highest first), then by evidence count
        valid.sort(key=lambda c: (c.confidence, len(c.evidence)), reverse=True)

        # Step 3: Select the strongest candidate
        accepted = valid[0]

        # Step 4: All remaining valid candidates that weren't selected are rejected
        rejected.extend(valid[1:])

        return accepted, rejected


class StageProgressionEngine:
    """
    8-stage deterministic pipeline for journey stage progression.

    This engine evaluates the current journey state against
    intelligence context and evidence to determine observed
    stage progression.

    It does NOT:
    - Recommend actions
    - Predict future stages
    - Estimate probabilities
    - Perform lead scoring
    - Execute workflows
    """

    def __init__(
        self,
        rule_registry: Optional[StageProgressionRuleRegistry] = None,
        resolver: Optional[StageTransitionResolver] = None,
    ) -> None:
        self._rule_registry = rule_registry or default_rule_registry
        self._resolver = resolver or StageTransitionResolver()
        self._processed_fingerprints: Dict[str, str] = {}

    def progress(self, context: JourneyProgressionContext) -> JourneyProgressionResult:
        """
        Execute the 8-stage deterministic progression pipeline.

        Args:
            context: Complete progression context with all intelligence inputs.

        Returns:
            JourneyProgressionResult with evidence-backed progression or NO_CHANGE.
        """
        pipeline_start = time.monotonic()
        stage_timings: Dict[str, float] = {}
        correlation_id = context.correlation_id or str(uuid.uuid4())
        causation_id = context.causation_id or ""

        # ── Stage 1: Load Journey State ──────────────────────────────────
        t0 = time.monotonic()
        journey_state = self._stage_1_load_state(context)
        stage_timings["load_state"] = (time.monotonic() - t0) * 1000

        # ── Stage 2: Load Journey Definition ─────────────────────────────
        t0 = time.monotonic()
        journey_definition = self._stage_2_load_definition(context)
        stage_timings["load_definition"] = (time.monotonic() - t0) * 1000

        # ── Stage 3: Load Intelligence Context ───────────────────────────
        t0 = time.monotonic()
        intent_ctx, conv_ctx, mem_ctx = self._stage_3_load_intelligence(context)
        stage_timings["load_intelligence"] = (time.monotonic() - t0) * 1000

        # ── Stage 4: Normalize Evidence ──────────────────────────────────
        t0 = time.monotonic()
        evidence = self._stage_4_normalize_evidence(context)
        stage_timings["normalize_evidence"] = (time.monotonic() - t0) * 1000

        # ── Stage 5: Generate Candidate Transitions ──────────────────────
        t0 = time.monotonic()
        candidates, rules_evaluated, rules_matched = self._stage_5_generate_candidates(
            context, journey_state, journey_definition,
        )
        stage_timings["generate_candidates"] = (time.monotonic() - t0) * 1000

        # ── Stage 6: Resolve Transition ──────────────────────────────────
        t0 = time.monotonic()
        accepted, rejected = self._stage_6_resolve(
            candidates, journey_definition, journey_state.current_stage,
        )
        stage_timings["resolve_transition"] = (time.monotonic() - t0) * 1000

        # ── Stage 7: Validate Progression ────────────────────────────────
        t0 = time.monotonic()
        validation_errors = self._stage_7_validate(
            context, journey_state, journey_definition, accepted,
        )
        stage_timings["validate_progression"] = (time.monotonic() - t0) * 1000

        # ── Stage 8: Generate Result ─────────────────────────────────────
        t0 = time.monotonic()

        # Check idempotency
        fingerprint = ""
        if accepted and accepted.transition_type != TransitionType.INITIALIZATION:
            evidence_ids = sorted(str(e.evidence_id) for e in accepted.evidence)
            fingerprint = journey_state.compute_progression_fingerprint(
                evidence_ids, journey_definition.version,
            )
            if fingerprint in self._processed_fingerprints:
                # Idempotent: return NO_CHANGE
                accepted = None
                rejected = candidates

        execution_time_ms = (time.monotonic() - pipeline_start) * 1000
        stage_timings["generate_result"] = (time.monotonic() - t0) * 1000

        diagnostics = JourneyDiagnostics(
            pipeline_version="1.0.0",
            stage_timings=stage_timings,
            rules_evaluated=rules_evaluated,
            rules_matched=rules_matched,
            candidate_transition_count=len(candidates),
            accepted_transition_count=1 if accepted else 0,
            rejected_transition_count=len(rejected),
            evidence_count=len(evidence),
            validation_errors=validation_errors,
            execution_time_ms=execution_time_ms,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

        provenance = JourneyProvenance(
            journey_version="2.4.2",
            definition_version=journey_definition.version,
            progression_engine_version="2.4.2",
            rule_pack_version="1.0.0",
            pipeline_version="1.0.0",
            generated_at=datetime.now(timezone.utc),
            source_modules=self._collect_source_modules(accepted),
            workspace_id=context.workspace_id,
        )

        result = self._stage_8_build_result(
            context, journey_state, journey_definition,
            accepted, rejected, evidence, diagnostics, provenance,
            fingerprint, validation_errors,
        )

        # Store fingerprint for idempotency
        if accepted and fingerprint:
            self._processed_fingerprints[fingerprint] = str(result.progression_id)

        return result

    # ── Pipeline Stage Implementations ───────────────────────────────────────

    def _stage_1_load_state(self, context: JourneyProgressionContext) -> JourneyState:
        """Stage 1: Load and validate journey state."""
        if context.journey_state is None:
            raise JourneyNotFoundError(entity_id=context.entity_id)
        return context.journey_state

    def _stage_2_load_definition(self, context: JourneyProgressionContext) -> JourneyDefinition:
        """Stage 2: Load and validate journey definition."""
        if context.journey_definition is None:
            raise JourneyDefinitionError("No journey definition provided in context")
        if not context.journey_definition.stage_definitions:
            raise JourneyDefinitionError("Journey definition has no stage definitions")
        return context.journey_definition

    def _stage_3_load_intelligence(
        self, context: JourneyProgressionContext,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Stage 3: Load intelligence context from upstream APIs."""
        return (
            context.intent_context,
            context.conversation_context,
            context.memory_context,
        )

    def _stage_4_normalize_evidence(
        self, context: JourneyProgressionContext,
    ) -> List[JourneyEvidence]:
        """Stage 4: Normalize and validate evidence."""
        evidence = list(context.evidence) if context.evidence else []

        # Validate workspace isolation for each evidence item
        if context.workspace_id:
            ws_str = str(context.workspace_id)
            for ev in evidence:
                ev_meta_ws = ev.metadata.get("workspace_id", "")
                if ev_meta_ws and str(ev_meta_ws) != ws_str:
                    raise WorkspaceIsolationError(ws_str, str(ev_meta_ws))

        return evidence

    def _stage_5_generate_candidates(
        self,
        context: JourneyProgressionContext,
        journey_state: JourneyState,
        journey_definition: JourneyDefinition,
    ) -> Tuple[List[TransitionCandidate], int, int]:
        """Stage 5: Evaluate all applicable rules and collect candidates."""
        current_stage = journey_state.current_stage
        journey_type = journey_definition.journey_type

        # Get applicable rules
        rules = self._rule_registry.get_rules_for_stage(journey_type, current_stage)

        candidates: List[TransitionCandidate] = []
        rules_evaluated = len(rules)
        rules_matched = 0

        for rule in rules:
            try:
                candidate = rule.evaluate(context)
                if candidate is not None:
                    candidates.append(candidate)
                    rules_matched += 1
            except Exception:
                # Rule evaluation failure should not crash the pipeline
                continue

        return candidates, rules_evaluated, rules_matched

    def _stage_6_resolve(
        self,
        candidates: List[TransitionCandidate],
        journey_definition: JourneyDefinition,
        current_stage: JourneyStageCode,
    ) -> Tuple[Optional[TransitionCandidate], List[TransitionCandidate]]:
        """Stage 6: Resolve transition conflicts."""
        return self._resolver.resolve(candidates, journey_definition, current_stage)

    def _stage_7_validate(
        self,
        context: JourneyProgressionContext,
        journey_state: JourneyState,
        journey_definition: JourneyDefinition,
        accepted: Optional[TransitionCandidate],
    ) -> List[str]:
        """Stage 7: Validate the proposed progression."""
        errors: List[str] = []

        if accepted is None:
            return errors

        # Validate evidence is not empty (except for initialization)
        if accepted.transition_type != TransitionType.INITIALIZATION:
            if not accepted.evidence:
                errors.append("Transition has no supporting evidence")

        # Validate confidence bounds
        if not (0.0 <= accepted.confidence <= 1.0):
            errors.append(f"Confidence {accepted.confidence} out of bounds [0.0, 1.0]")

        # Validate entity consistency
        if context.entity_id and journey_state.entity_id:
            if context.entity_id != journey_state.entity_id:
                errors.append(
                    f"Entity mismatch: context={context.entity_id}, "
                    f"state={journey_state.entity_id}"
                )

        # Validate workspace consistency
        if context.workspace_id and journey_state.workspace_id:
            if str(context.workspace_id) != str(journey_state.workspace_id):
                errors.append(
                    f"Workspace mismatch: context={context.workspace_id}, "
                    f"state={journey_state.workspace_id}"
                )

        # Validate terminal stage (should not transition from terminal)
        stage_def = journey_definition.get_stage_definition(journey_state.current_stage)
        if stage_def and stage_def.is_terminal:
            if accepted.transition_type != TransitionType.REACTIVATION:
                errors.append(
                    f"Cannot transition from terminal stage {journey_state.current_stage.value}"
                )

        return errors

    def _stage_8_build_result(
        self,
        context: JourneyProgressionContext,
        journey_state: JourneyState,
        journey_definition: JourneyDefinition,
        accepted: Optional[TransitionCandidate],
        rejected: List[TransitionCandidate],
        evidence: List[JourneyEvidence],
        diagnostics: JourneyDiagnostics,
        provenance: JourneyProvenance,
        fingerprint: str,
        validation_errors: List[str],
    ) -> JourneyProgressionResult:
        """Stage 8: Build the final progression result."""
        now = datetime.now(timezone.utc)

        if accepted is None or validation_errors:
            # NO CHANGE
            return JourneyProgressionResult(
                progression_id=uuid.uuid4(),
                journey_instance_id=journey_state.journey_instance_id,
                workspace_id=context.workspace_id,
                entity_type=context.entity_type,
                entity_id=context.entity_id,
                previous_stage=journey_state.previous_stage,
                current_stage=journey_state.current_stage,
                new_stage=None,
                transition=None,
                transition_type=None,
                timeline_event=None,
                did_progress=False,
                confidence=0.0,
                confidence_factors=None,
                evidence=evidence,
                accepted_candidate=None,
                rejected_candidates=rejected,
                diagnostics=diagnostics,
                provenance=provenance,
                generated_at=now,
                idempotency_fingerprint=fingerprint,
                new_state=journey_state,
            )

        # Build the transition
        transition = JourneyStageTransition(
            transition_id=uuid.uuid4(),
            journey_instance_id=journey_state.journey_instance_id,
            workspace_id=context.workspace_id,
            from_stage=accepted.from_stage,
            to_stage=accepted.to_stage,
            transition_type=accepted.transition_type,
            occurred_at=now,
            evidence=accepted.evidence,
            source_modules=accepted.source_modules,
            confidence=accepted.confidence,
            confidence_factors=accepted.confidence_factors,
            reason=accepted.reason,
            provenance=provenance,
        )

        # Build timeline event
        event_type = self._map_transition_to_timeline_event(accepted.transition_type)
        timeline_event = JourneyTimelineEvent(
            event_id=uuid.uuid4(),
            journey_instance_id=journey_state.journey_instance_id,
            workspace_id=context.workspace_id,
            event_type=event_type,
            stage=accepted.to_stage,
            previous_stage=accepted.from_stage,
            timestamp=now,
            evidence=accepted.evidence,
            confidence=accepted.confidence,
        )

        new_state = JourneyState(
            journey_instance_id=journey_state.journey_instance_id,
            workspace_id=journey_state.workspace_id,
            entity_type=journey_state.entity_type,
            entity_id=journey_state.entity_id,
            journey_definition_id=journey_state.journey_definition_id,
            journey_definition_version=journey_state.journey_definition_version,
            current_stage=accepted.to_stage,
            previous_stage=journey_state.current_stage,
            stage_entered_at=now,
            last_transition_at=now,
            status=journey_state.status,
            stage_history=list(journey_state.stage_history) + [accepted.to_stage],
            transitions=list(journey_state.transitions) + [transition],
            timeline=journey_state.timeline,
            metadata=journey_state.metadata,
        )

        return JourneyProgressionResult(
            progression_id=uuid.uuid4(),
            journey_instance_id=journey_state.journey_instance_id,
            workspace_id=context.workspace_id,
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            previous_stage=accepted.from_stage,
            current_stage=journey_state.current_stage,
            new_stage=accepted.to_stage,
            transition=transition,
            transition_type=accepted.transition_type,
            timeline_event=timeline_event,
            did_progress=True,
            confidence=accepted.confidence,
            confidence_factors=accepted.confidence_factors,
            evidence=accepted.evidence,
            accepted_candidate=accepted,
            rejected_candidates=rejected,
            diagnostics=diagnostics,
            provenance=provenance,
            generated_at=now,
            idempotency_fingerprint=fingerprint,
            new_state=new_state,
        )

    def _map_transition_to_timeline_event(self, transition_type: TransitionType) -> TimelineEventType:
        """Map a transition type to the appropriate timeline event type."""
        mapping = {
            TransitionType.INITIALIZATION: TimelineEventType.STAGE_ENTERED,
            TransitionType.ADVANCE: TimelineEventType.STAGE_ADVANCED,
            TransitionType.REGRESSION: TimelineEventType.STAGE_REGRESSED,
            TransitionType.REACTIVATION: TimelineEventType.STAGE_REACTIVATED,
            TransitionType.COMPLETION: TimelineEventType.STAGE_COMPLETED,
            TransitionType.CLOSURE: TimelineEventType.JOURNEY_CLOSED,
            TransitionType.LATERAL: TimelineEventType.STAGE_ENTERED,
            TransitionType.CUSTOM: TimelineEventType.STAGE_ENTERED,
        }
        return mapping.get(transition_type, TimelineEventType.STAGE_ENTERED)

    def _collect_source_modules(self, accepted: Optional[TransitionCandidate]) -> List[str]:
        """Collect source module names from the accepted candidate."""
        modules = ["journey.progression"]
        if accepted:
            for mod in accepted.source_modules:
                if mod not in modules:
                    modules.append(mod)
        return modules


# Module-level singleton
default_progression_engine: StageProgressionEngine = StageProgressionEngine()
