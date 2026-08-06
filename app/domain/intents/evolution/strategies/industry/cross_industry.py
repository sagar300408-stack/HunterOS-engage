"""
HunterOS Engage V1 - Cross-Industry Evolution Strategy
Standard commercial and operational intent progression rules.
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
    IntentStateTransition,
)
from app.domain.intents.evolution.strategies.base import (
    AbstractEvolutionStrategy,
    StrategyEvaluationResult,
)

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class CrossIndustryEvolutionStrategy(AbstractEvolutionStrategy):
    """
    Evaluates cross-industry commercial lifecycle steps:
    Inquiry -> Negotiation -> Agreement/Resolution -> Closed.
    """

    def __init__(self, strategy_version: str = "1.0.0"):
        super().__init__(
            strategy_id="CrossIndustryEvolutionStrategy",
            strategy_version=strategy_version,
            description="Evaluates cross-industry commercial and transactional progression.",
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
            # Check for explicit resolution markers in metadata
            is_resolved = curr.metadata.get("is_resolved", False)
            is_closed = curr.metadata.get("is_closed", False)

            if is_resolved:
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_RESOLVED,
                    previous_state=IntentLifecycleState.ACTIVE,
                    current_state=IntentLifecycleState.RESOLVED,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[curr.conversation_id],
                    provenance=provenance,
                    metadata={"resolved_via": curr.metadata.get("resolved_reason", "explicit")},
                )
                events.append(event)
                transitions.append(
                    IntentStateTransition(
                        from_state=IntentLifecycleState.ACTIVE,
                        to_state=IntentLifecycleState.RESOLVED,
                        transition_reason=f"Intent marked resolved in conversation {curr.conversation_id}.",
                        transitioned_at=curr.observed_at,
                        trigger_event_type=IntentEvolutionEventType.INTENT_RESOLVED,
                        confidence_delta=0.0,
                    )
                )

            elif is_closed:
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_CLOSED,
                    previous_state=IntentLifecycleState.ACTIVE,
                    current_state=IntentLifecycleState.CLOSED,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[curr.conversation_id],
                    provenance=provenance,
                    metadata={"closed_via": curr.metadata.get("closed_reason", "explicit")},
                )
                events.append(event)
                transitions.append(
                    IntentStateTransition(
                        from_state=IntentLifecycleState.ACTIVE,
                        to_state=IntentLifecycleState.CLOSED,
                        transition_reason=f"Intent closed in conversation {curr.conversation_id}.",
                        transitioned_at=curr.observed_at,
                        trigger_event_type=IntentEvolutionEventType.INTENT_CLOSED,
                        confidence_delta=0.0,
                    )
                )

        return StrategyEvaluationResult(events=events, transitions=transitions)
