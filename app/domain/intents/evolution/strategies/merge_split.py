"""
HunterOS Engage V1 - Merge & Split Evolution Strategies
Detects intentional intent mergers (consolidation) and intent splits (divergence).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Set
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


class MergeStrategy(AbstractEvolutionStrategy):
    """
    Detects when multiple historical sub-intents are consolidated into a unified parent intent.
    """

    def __init__(self, strategy_version: str = "1.0.0"):
        super().__init__(
            strategy_id="StandardMergeStrategy",
            strategy_version=strategy_version,
            description="Detects consolidation of multiple prior intents into a unified intent.",
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

        # Look for merge relationships or taxonomy ancestor subsumptions
        for curr in context.current_snapshots:
            merged_intent_ids: List[str] = curr.metadata.get("merged_intent_ids", [])
            if merged_intent_ids:
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_MERGED,
                    previous_state=IntentLifecycleState.ACTIVE,
                    current_state=IntentLifecycleState.MERGED,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[curr.conversation_id],
                    provenance=provenance,
                    metadata={"merged_intent_ids": merged_intent_ids},
                )
                events.append(event)

                transitions.append(
                    IntentStateTransition(
                        from_state=IntentLifecycleState.ACTIVE,
                        to_state=IntentLifecycleState.MERGED,
                        transition_reason=f"Merged {len(merged_intent_ids)} prior intents into '{curr.taxonomy_path}'.",
                        transitioned_at=curr.observed_at,
                        trigger_event_type=IntentEvolutionEventType.INTENT_MERGED,
                        confidence_delta=0.0,
                        metadata={"merged_count": len(merged_intent_ids)},
                    )
                )

        return StrategyEvaluationResult(events=events, transitions=transitions)


class SplitStrategy(AbstractEvolutionStrategy):
    """
    Detects when a historical broad intent branches into multiple distinct granular sub-intents.
    """

    def __init__(self, strategy_version: str = "1.0.0"):
        super().__init__(
            strategy_id="StandardSplitStrategy",
            strategy_version=strategy_version,
            description="Detects divergence of a single broad intent into multiple granular intents.",
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

        for curr in context.current_snapshots:
            split_from_id: Optional[str] = curr.metadata.get("split_from_intent_id")
            if split_from_id:
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_SPLIT,
                    previous_state=IntentLifecycleState.ACTIVE,
                    current_state=IntentLifecycleState.SPLIT,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[curr.conversation_id],
                    provenance=provenance,
                    metadata={"split_from_intent_id": split_from_id},
                )
                events.append(event)

                transitions.append(
                    IntentStateTransition(
                        from_state=IntentLifecycleState.ACTIVE,
                        to_state=IntentLifecycleState.SPLIT,
                        transition_reason=f"Split from prior intent {split_from_id} into '{curr.taxonomy_path}'.",
                        transitioned_at=curr.observed_at,
                        trigger_event_type=IntentEvolutionEventType.INTENT_SPLIT,
                        confidence_delta=0.0,
                        metadata={"split_from": split_from_id},
                    )
                )

        return StrategyEvaluationResult(events=events, transitions=transitions)
