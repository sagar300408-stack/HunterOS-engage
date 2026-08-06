"""
HunterOS Engage V1 - Transition Evolution Strategy
Validates state transitions and emits reclassification / state migration events.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List
import uuid

from app.domain.intents.evolution.models import (
    EvolutionProvenance,
    IntentEvolutionEvent,
    IntentEvolutionEventType,
    IntentLifecycleState,
    IntentStateSnapshot,
    IntentStateTransition,
)
from app.domain.intents.evolution.strategies.base import (
    AbstractEvolutionStrategy,
    StrategyEvaluationResult,
)

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class TransitionStrategy(AbstractEvolutionStrategy):
    """
    Detects reclassification (e.g. category or taxonomy shifts) and formal state transitions.
    """

    def __init__(self, strategy_version: str = "1.0.0"):
        super().__init__(
            strategy_id="StandardTransitionStrategy",
            strategy_version=strategy_version,
            description="Detects reclassifications and lifecycle state migrations.",
        )

    def evaluate(self, context: IntentEvolutionContext) -> StrategyEvaluationResult:
        events: List[IntentEvolutionEvent] = []
        transitions: List[IntentStateTransition] = []

        now = datetime.now(timezone.utc)
        provenance = EvolutionProvenance(
            evolution_version="1.0.0",
            strategy_version=self.strategy_version,
            generator_version="1.0.0",
            generated_at=now,
        )

        hist_by_id: Dict[uuid.UUID, IntentStateSnapshot] = {
            h.intent_id: h for h in context.historical_snapshots
        }

        for curr in context.current_snapshots:
            hist_match = hist_by_id.get(curr.intent_id)
            if hist_match and (
                hist_match.taxonomy_path != curr.taxonomy_path
                or hist_match.category != curr.category
            ):
                # RECLASSIFIED / CHANGED
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_RECLASSIFIED,
                    previous_state=IntentLifecycleState.ACTIVE,
                    current_state=IntentLifecycleState.CHANGED,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[hist_match.conversation_id, curr.conversation_id],
                    provenance=provenance,
                    metadata={
                        "previous_taxonomy_path": hist_match.taxonomy_path,
                        "current_taxonomy_path": curr.taxonomy_path,
                        "previous_category": hist_match.category,
                        "current_category": curr.category,
                    },
                )
                events.append(event)

                transitions.append(
                    IntentStateTransition(
                        from_state=IntentLifecycleState.ACTIVE,
                        to_state=IntentLifecycleState.CHANGED,
                        transition_reason=f"Taxonomy shifted from '{hist_match.taxonomy_path}' to '{curr.taxonomy_path}'.",
                        transitioned_at=curr.observed_at,
                        trigger_event_type=IntentEvolutionEventType.INTENT_RECLASSIFIED,
                        confidence_delta=round(curr.confidence - hist_match.confidence, 4),
                        metadata={"new_taxonomy": curr.taxonomy_path},
                    )
                )

        return StrategyEvaluationResult(events=events, transitions=transitions)
