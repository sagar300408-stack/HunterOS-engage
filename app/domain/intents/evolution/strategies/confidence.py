"""
HunterOS Engage V1 - Confidence Evolution Strategy
Evaluates confidence deltas to detect STRENGTHENING (delta >= +0.05) or WEAKENING (delta <= -0.05).
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


class ConfidenceStrategy(AbstractEvolutionStrategy):
    """
    Evaluates confidence shifts across observations to detect STRENGTHENING and WEAKENING.
    """

    def __init__(
        self,
        strategy_version: str = "1.0.0",
        strengthening_threshold: float = 0.05,
        weakening_threshold: float = -0.05,
    ):
        super().__init__(
            strategy_id="StandardConfidenceStrategy",
            strategy_version=strategy_version,
            description="Evaluates confidence changes across snapshots to detect STRENGTHENING or WEAKENING.",
        )
        self.strengthening_threshold: float = strengthening_threshold
        self.weakening_threshold: float = weakening_threshold

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

        hist_by_path: Dict[str, IntentStateSnapshot] = {
            h.taxonomy_path: h for h in context.historical_snapshots
        }

        for curr in context.current_snapshots:
            hist_match = hist_by_path.get(curr.taxonomy_path)
            if not hist_match:
                continue

            delta = round(curr.confidence - hist_match.confidence, 4)

            if delta >= self.strengthening_threshold:
                # STRENGTHENING
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_STRENGTH_INCREASED,
                    previous_state=IntentLifecycleState.ACTIVE,
                    current_state=IntentLifecycleState.STRENGTHENING,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[hist_match.conversation_id, curr.conversation_id],
                    provenance=provenance,
                    metadata={
                        "previous_confidence": hist_match.confidence,
                        "current_confidence": curr.confidence,
                        "confidence_delta": delta,
                    },
                )
                events.append(event)

                transitions.append(
                    IntentStateTransition(
                        from_state=IntentLifecycleState.ACTIVE,
                        to_state=IntentLifecycleState.STRENGTHENING,
                        transition_reason=f"Confidence increased by {delta:+.2f} ({hist_match.confidence:.2f} -> {curr.confidence:.2f}).",
                        transitioned_at=curr.observed_at,
                        trigger_event_type=IntentEvolutionEventType.INTENT_STRENGTH_INCREASED,
                        confidence_delta=delta,
                        metadata={"delta": delta},
                    )
                )

            elif delta <= self.weakening_threshold:
                # WEAKENING
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_STRENGTH_DECREASED,
                    previous_state=IntentLifecycleState.ACTIVE,
                    current_state=IntentLifecycleState.WEAKENING,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[hist_match.conversation_id, curr.conversation_id],
                    provenance=provenance,
                    metadata={
                        "previous_confidence": hist_match.confidence,
                        "current_confidence": curr.confidence,
                        "confidence_delta": delta,
                    },
                )
                events.append(event)

                transitions.append(
                    IntentStateTransition(
                        from_state=IntentLifecycleState.ACTIVE,
                        to_state=IntentLifecycleState.WEAKENING,
                        transition_reason=f"Confidence decreased by {delta:+.2f} ({hist_match.confidence:.2f} -> {curr.confidence:.2f}).",
                        transitioned_at=curr.observed_at,
                        trigger_event_type=IntentEvolutionEventType.INTENT_STRENGTH_DECREASED,
                        confidence_delta=delta,
                        metadata={"delta": delta},
                    )
                )

        return StrategyEvaluationResult(events=events, transitions=transitions)
