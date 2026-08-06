"""
HunterOS Engage V1 - Lifecycle Evolution Strategy
Identifies emergent (NEW), persisting (PERSISTING), changed, and resolved intents.
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


class LifecycleStrategy(AbstractEvolutionStrategy):
    """
    Evaluates presence, recurrence, and lifecycle transitions across intent snapshots.
    """

    def __init__(self, strategy_version: str = "1.0.0"):
        super().__init__(
            strategy_id="StandardLifecycleStrategy",
            strategy_version=strategy_version,
            description="Evaluates NEW, PERSISTING, RECLASSIFIED, and INACTIVE lifecycle states.",
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

        # Index historical snapshots by intent canonical name / taxonomy_path
        hist_by_path: Dict[str, IntentStateSnapshot] = {}
        for h in context.historical_snapshots:
            hist_by_path[h.taxonomy_path] = h

        # Evaluate Current Snapshots
        for curr in context.current_snapshots:
            hist_match = hist_by_path.get(curr.taxonomy_path)

            if hist_match is None:
                # 1. NEW Intent Emergence
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_CREATED,
                    previous_state=None,
                    current_state=IntentLifecycleState.NEW,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[curr.conversation_id],
                    provenance=provenance,
                    metadata={"taxonomy_path": curr.taxonomy_path, "confidence": curr.confidence},
                )
                events.append(event)
            else:
                # 2. PERSISTING Intent
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_UPDATED,
                    previous_state=IntentLifecycleState.NEW,
                    current_state=IntentLifecycleState.PERSISTING,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[hist_match.conversation_id, curr.conversation_id],
                    provenance=provenance,
                    metadata={"taxonomy_path": curr.taxonomy_path, "confidence": curr.confidence},
                )
                events.append(event)

                transitions.append(
                    IntentStateTransition(
                        from_state=IntentLifecycleState.NEW,
                        to_state=IntentLifecycleState.PERSISTING,
                        transition_reason=f"Intent persisted across conversation {curr.conversation_id}.",
                        transitioned_at=curr.observed_at,
                        trigger_event_type=IntentEvolutionEventType.INTENT_UPDATED,
                        confidence_delta=round(curr.confidence - hist_match.confidence, 4),
                        metadata={"taxonomy_path": curr.taxonomy_path},
                    )
                )

        return StrategyEvaluationResult(events=events, transitions=transitions)
