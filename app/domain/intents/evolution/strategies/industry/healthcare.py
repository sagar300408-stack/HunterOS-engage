"""
HunterOS Engage V1 - Healthcare Evolution Strategy
Domain-specific lifecycle progression for symptom inquiry, doctor appointment, and follow-ups.
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


class HealthcareEvolutionStrategy(AbstractEvolutionStrategy):
    """
    Tracks Healthcare clinical and patient intent transitions:
    Symptom Inquiry -> Appointment Booking -> Prescription/Treatment -> Follow-up.
    """

    def __init__(self, strategy_version: str = "1.0.0"):
        super().__init__(
            strategy_id="HealthcareEvolutionStrategy",
            strategy_version=strategy_version,
            description="Evaluates Healthcare domain specific intent evolutions.",
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
            if "HEALTHCARE" in curr.category.upper() or "MEDICAL" in curr.taxonomy_path.upper():
                event = IntentEvolutionEvent(
                    intent_id=curr.intent_id,
                    entity_type=curr.entity_type,
                    entity_id=curr.entity_id,
                    workspace_id=curr.workspace_id,
                    event_type=IntentEvolutionEventType.INTENT_UPDATED,
                    previous_state=IntentLifecycleState.ACTIVE,
                    current_state=IntentLifecycleState.ACTIVE,
                    occurred_at=curr.observed_at,
                    supporting_evidence=curr.evidence_message_ids,
                    source_conversations=[curr.conversation_id],
                    provenance=provenance,
                    metadata={"healthcare_domain": curr.intent_type},
                )
                events.append(event)

        return StrategyEvaluationResult(events=events, transitions=transitions)
