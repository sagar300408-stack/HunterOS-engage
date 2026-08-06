"""
HunterOS Engage V1 - Intent Evolution Validation Framework
Zero-trust guardrails, transition matrix verification, and tenant isolation checks.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
import uuid

from app.domain.intents.evolution.models import (
    IntentEvolutionEvent,
    IntentLifecycleState,
    IntentStateTransition,
    IntentTimeline,
)


class EvolutionValidationError(Exception):
    """Raised when an unrecoverable evolution invariant is violated."""
    pass


class EvolutionValidator:
    """
    Validates temporal integrity, legal lifecycle transitions, and cross-workspace isolation.
    """

    # Permitted state transition matrix
    LEGAL_TRANSITIONS: Dict[IntentLifecycleState, Set[IntentLifecycleState]] = {
        IntentLifecycleState.NEW: {
            IntentLifecycleState.NEW,
            IntentLifecycleState.ACTIVE,
            IntentLifecycleState.PERSISTING,
            IntentLifecycleState.RESOLVED,
            IntentLifecycleState.CLOSED,
            IntentLifecycleState.INACTIVE,
        },
        IntentLifecycleState.ACTIVE: {
            IntentLifecycleState.ACTIVE,
            IntentLifecycleState.PERSISTING,
            IntentLifecycleState.STRENGTHENING,
            IntentLifecycleState.WEAKENING,
            IntentLifecycleState.CHANGED,
            IntentLifecycleState.MERGED,
            IntentLifecycleState.SPLIT,
            IntentLifecycleState.RESOLVED,
            IntentLifecycleState.INACTIVE,
            IntentLifecycleState.CLOSED,
        },
        IntentLifecycleState.PERSISTING: {
            IntentLifecycleState.PERSISTING,
            IntentLifecycleState.ACTIVE,
            IntentLifecycleState.STRENGTHENING,
            IntentLifecycleState.WEAKENING,
            IntentLifecycleState.CHANGED,
            IntentLifecycleState.MERGED,
            IntentLifecycleState.SPLIT,
            IntentLifecycleState.RESOLVED,
            IntentLifecycleState.INACTIVE,
            IntentLifecycleState.CLOSED,
        },
        IntentLifecycleState.STRENGTHENING: {
            IntentLifecycleState.STRENGTHENING,
            IntentLifecycleState.PERSISTING,
            IntentLifecycleState.ACTIVE,
            IntentLifecycleState.WEAKENING,
            IntentLifecycleState.CHANGED,
            IntentLifecycleState.MERGED,
            IntentLifecycleState.SPLIT,
            IntentLifecycleState.RESOLVED,
            IntentLifecycleState.INACTIVE,
            IntentLifecycleState.CLOSED,
        },
        IntentLifecycleState.WEAKENING: {
            IntentLifecycleState.WEAKENING,
            IntentLifecycleState.PERSISTING,
            IntentLifecycleState.ACTIVE,
            IntentLifecycleState.STRENGTHENING,
            IntentLifecycleState.CHANGED,
            IntentLifecycleState.MERGED,
            IntentLifecycleState.SPLIT,
            IntentLifecycleState.RESOLVED,
            IntentLifecycleState.INACTIVE,
            IntentLifecycleState.CLOSED,
        },
        IntentLifecycleState.CHANGED: {
            IntentLifecycleState.CHANGED,
            IntentLifecycleState.ACTIVE,
            IntentLifecycleState.PERSISTING,
            IntentLifecycleState.STRENGTHENING,
            IntentLifecycleState.WEAKENING,
            IntentLifecycleState.RESOLVED,
            IntentLifecycleState.CLOSED,
            IntentLifecycleState.INACTIVE,
        },
        IntentLifecycleState.MERGED: {
            IntentLifecycleState.MERGED,
            IntentLifecycleState.RESOLVED,
            IntentLifecycleState.CLOSED,
            IntentLifecycleState.INACTIVE,
        },
        IntentLifecycleState.SPLIT: {
            IntentLifecycleState.SPLIT,
            IntentLifecycleState.RESOLVED,
            IntentLifecycleState.CLOSED,
            IntentLifecycleState.INACTIVE,
        },
        IntentLifecycleState.RESOLVED: {
            IntentLifecycleState.RESOLVED,
            IntentLifecycleState.CLOSED,
            IntentLifecycleState.ACTIVE,
            IntentLifecycleState.PERSISTING,
            IntentLifecycleState.INACTIVE,
        },
        IntentLifecycleState.INACTIVE: {
            IntentLifecycleState.INACTIVE,
            IntentLifecycleState.ACTIVE,
            IntentLifecycleState.PERSISTING,
            IntentLifecycleState.CLOSED,
        },
        IntentLifecycleState.CLOSED: {
            IntentLifecycleState.CLOSED,
            IntentLifecycleState.ACTIVE,
        },
    }

    def validate_timeline_consistency(self, timeline: IntentTimeline) -> List[str]:
        """Verify chronological monotonicity and valid transition sequences."""
        errors: List[str] = []

        if timeline.first_detected_at > timeline.last_observed_at:
            errors.append(
                f"Temporal monotonicity violation: Timeline '{timeline.intent_id}' first_detected_at ({timeline.first_detected_at}) "
                f"cannot be after last_observed_at ({timeline.last_observed_at})."
            )

        if timeline.observation_frequency < 1:
            errors.append(f"Timeline '{timeline.intent_id}': observation_frequency must be >= 1.")

        # Check transition chronological monotonicity
        last_dt = timeline.first_detected_at
        for tr in timeline.state_transitions:
            if tr.transitioned_at < last_dt:
                errors.append(
                    f"Timeline '{timeline.intent_id}': Transition {tr.transition_id} transitioned_at "
                    f"({tr.transitioned_at}) is earlier than previous timestamp ({last_dt})."
                )
            last_dt = tr.transitioned_at

            # Check legal state transition
            if not self.is_legal_transition(tr.from_state, tr.to_state):
                errors.append(
                    f"Timeline '{timeline.intent_id}': Illegal state transition from "
                    f"'{tr.from_state.value}' to '{tr.to_state.value}'."
                )

        return errors

    def validate_transition(self, transition: IntentStateTransition) -> List[str]:
        """Validate an individual state transition."""
        errors: List[str] = []
        if not self.is_legal_transition(transition.from_state, transition.to_state):
            errors.append(
                f"Illegal state transition from '{transition.from_state.value}' to '{transition.to_state.value}'."
            )
        return errors

    def is_legal_transition(
        self, from_state: IntentLifecycleState, to_state: IntentLifecycleState
    ) -> bool:
        """Check if transition from one lifecycle state to another is permitted."""
        allowed = self.LEGAL_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    def validate_events(self, events: List[IntentEvolutionEvent]) -> List[str]:
        """Validate events for duplicates and structural consistency."""
        errors: List[str] = []
        seen_keys: Set[Tuple[uuid.UUID, str, str]] = set()

        for ev in events:
            key = (ev.intent_id, ev.event_type.value, ev.occurred_at.isoformat())
            if key in seen_keys:
                errors.append(
                    f"Duplicate evolution event detected: intent_id={ev.intent_id}, "
                    f"type={ev.event_type.value}, occurred_at={ev.occurred_at}."
                )
            seen_keys.add(key)

        return errors

    def validate_workspace_isolation(
        self,
        workspace_id: Optional[uuid.UUID],
        events: List[IntentEvolutionEvent],
    ) -> List[str]:
        """Ensure no cross-tenant contamination in evolution events."""
        errors: List[str] = []
        if not workspace_id:
            return errors

        for ev in events:
            if ev.workspace_id and ev.workspace_id != workspace_id:
                errors.append(
                    f"Cross-workspace isolation breach: Event {ev.event_id} has workspace_id="
                    f"{ev.workspace_id}, expected {workspace_id}."
                )

        return errors

    def validate_confidence(self, confidence: float, context_desc: str = "") -> List[str]:
        """Ensure confidence values remain strictly within [0.0, 1.0]."""
        errors: List[str] = []
        if not (0.0 <= confidence <= 1.0):
            errors.append(
                f"Confidence value {confidence} in '{context_desc}' out of bounds [0.0, 1.0]."
            )
        return errors


default_evolution_validator = EvolutionValidator()
