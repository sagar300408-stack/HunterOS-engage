"""
HunterOS Engage V1 - Real Estate Evolution Strategy
Domain-specific lifecycle progression for property discovery, valuation, site visits, and booking.
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


class RealEstateEvolutionStrategy(AbstractEvolutionStrategy):
    """
    Tracks Real Estate intent transitions:
    Property Inquiry -> Price Inquiry -> Site Visit Request -> Booking -> Cancellation/Resolution.
    """

    def __init__(self, strategy_version: str = "1.0.0"):
        super().__init__(
            strategy_id="RealEstateEvolutionStrategy",
            strategy_version=strategy_version,
            description="Evaluates Real Estate domain specific intent evolutions.",
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
            if "REAL_ESTATE" in curr.category.upper() or "PROPERTY" in curr.taxonomy_path.upper():
                # Check for booking completion or site visit scheduling
                if "SITE_VISIT" in curr.intent_type.upper() or "BOOKING" in curr.intent_type.upper():
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
                        metadata={"real_estate_stage": curr.intent_type},
                    )
                    events.append(event)

        return StrategyEvaluationResult(events=events, transitions=transitions)
