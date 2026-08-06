"""
Unit tests for Intent Evolution Strategies and EvolutionStrategyRegistry.
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.evolution.context import IntentEvolutionContext
from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEventType,
    IntentLifecycleState,
    IntentStateSnapshot,
)
from app.domain.intents.evolution.strategies.confidence import ConfidenceStrategy
from app.domain.intents.evolution.strategies.industry.cross_industry import CrossIndustryEvolutionStrategy
from app.domain.intents.evolution.strategies.industry.healthcare import HealthcareEvolutionStrategy
from app.domain.intents.evolution.strategies.industry.real_estate import RealEstateEvolutionStrategy
from app.domain.intents.evolution.strategies.lifecycle import LifecycleStrategy
from app.domain.intents.evolution.strategies.merge_split import MergeStrategy, SplitStrategy
from app.domain.intents.evolution.strategies.registry import (
    EvolutionStrategyRegistry,
)
from app.domain.intents.evolution.strategies.transition import TransitionStrategy


def test_lifecycle_strategy_new_intent():
    intent_id = uuid.uuid4()
    context = IntentEvolutionContext(entity_id="cust-1", current_conversation_id="conv-1")

    context.current_snapshots = [
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="conv-1",
            intent_type="PricingInquiry",
            category="Sales",
            taxonomy_path="Sales/Pricing",
            confidence=0.85,
        )
    ]

    strat = LifecycleStrategy()
    res = strat.evaluate(context)

    assert len(res.events) == 1
    assert res.events[0].event_type == IntentEvolutionEventType.INTENT_CREATED
    assert res.events[0].current_state == IntentLifecycleState.NEW


def test_lifecycle_strategy_persisting_intent():
    intent_id = uuid.uuid4()
    context = IntentEvolutionContext(entity_id="cust-1", current_conversation_id="conv-2")

    context.historical_snapshots = [
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="conv-1",
            intent_type="PricingInquiry",
            category="Sales",
            taxonomy_path="Sales/Pricing",
            confidence=0.85,
        )
    ]

    context.current_snapshots = [
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="conv-2",
            intent_type="PricingInquiry",
            category="Sales",
            taxonomy_path="Sales/Pricing",
            confidence=0.88,
        )
    ]

    strat = LifecycleStrategy()
    res = strat.evaluate(context)

    assert len(res.events) == 1
    assert res.events[0].event_type == IntentEvolutionEventType.INTENT_UPDATED
    assert res.events[0].current_state == IntentLifecycleState.PERSISTING
    assert len(res.transitions) == 1
    assert res.transitions[0].from_state == IntentLifecycleState.NEW
    assert res.transitions[0].to_state == IntentLifecycleState.PERSISTING


def test_confidence_strategy_strengthening_and_weakening():
    intent_id1 = uuid.uuid4()
    intent_id2 = uuid.uuid4()
    context = IntentEvolutionContext(entity_id="cust-1", current_conversation_id="conv-2")

    context.historical_snapshots = [
        IntentStateSnapshot(
            intent_id=intent_id1,
            entity_id="cust-1",
            conversation_id="conv-1",
            intent_type="PricingInquiry",
            category="Sales",
            taxonomy_path="Sales/Pricing",
            confidence=0.70,
        ),
        IntentStateSnapshot(
            intent_id=intent_id2,
            entity_id="cust-1",
            conversation_id="conv-1",
            intent_type="SupportInquiry",
            category="Support",
            taxonomy_path="Support/Technical",
            confidence=0.90,
        ),
    ]

    context.current_snapshots = [
        IntentStateSnapshot(
            intent_id=intent_id1,
            entity_id="cust-1",
            conversation_id="conv-2",
            intent_type="PricingInquiry",
            category="Sales",
            taxonomy_path="Sales/Pricing",
            confidence=0.88,  # +0.18 -> STRENGTHENING
        ),
        IntentStateSnapshot(
            intent_id=intent_id2,
            entity_id="cust-1",
            conversation_id="conv-2",
            intent_type="SupportInquiry",
            category="Support",
            taxonomy_path="Support/Technical",
            confidence=0.72,  # -0.18 -> WEAKENING
        ),
    ]

    strat = ConfidenceStrategy()
    res = strat.evaluate(context)

    assert len(res.events) == 2
    types = [e.event_type for e in res.events]
    assert IntentEvolutionEventType.INTENT_STRENGTH_INCREASED in types
    assert IntentEvolutionEventType.INTENT_STRENGTH_DECREASED in types


def test_transition_strategy_reclassified():
    intent_id = uuid.uuid4()
    context = IntentEvolutionContext(entity_id="cust-1", current_conversation_id="conv-2")

    context.historical_snapshots = [
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="conv-1",
            intent_type="GeneralInquiry",
            category="General",
            taxonomy_path="General/Info",
            confidence=0.75,
        )
    ]

    context.current_snapshots = [
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="conv-2",
            intent_type="GeneralInquiry",
            category="Sales",
            taxonomy_path="Sales/Enterprise/Info",
            confidence=0.85,
        )
    ]

    strat = TransitionStrategy()
    res = strat.evaluate(context)

    assert len(res.events) == 1
    assert res.events[0].event_type == IntentEvolutionEventType.INTENT_RECLASSIFIED
    assert res.events[0].current_state == IntentLifecycleState.CHANGED


def test_merge_and_split_strategies():
    context = IntentEvolutionContext(entity_id="cust-1", current_conversation_id="conv-2")

    merged_id = uuid.uuid4()
    split_id = uuid.uuid4()

    context.current_snapshots = [
        IntentStateSnapshot(
            intent_id=merged_id,
            entity_id="cust-1",
            conversation_id="conv-2",
            intent_type="ConsolidatedCommercial",
            category="Sales",
            taxonomy_path="Sales/Commercial",
            confidence=0.95,
            metadata={"merged_intent_ids": ["prior-1", "prior-2"]},
        ),
        IntentStateSnapshot(
            intent_id=split_id,
            entity_id="cust-1",
            conversation_id="conv-2",
            intent_type="SpecificSubIntent",
            category="Sales",
            taxonomy_path="Sales/Specific",
            confidence=0.90,
            metadata={"split_from_intent_id": "broad-prior-1"},
        ),
    ]

    merge_res = MergeStrategy().evaluate(context)
    assert len(merge_res.events) == 1
    assert merge_res.events[0].event_type == IntentEvolutionEventType.INTENT_MERGED

    split_res = SplitStrategy().evaluate(context)
    assert len(split_res.events) == 1
    assert split_res.events[0].event_type == IntentEvolutionEventType.INTENT_SPLIT


def test_industry_and_custom_registry():
    registry = EvolutionStrategyRegistry(register_defaults=True)
    strategies = registry.list_strategies()
    assert len(strategies) >= 8

    # Custom Strategy
    from app.domain.intents.evolution.strategies.base import AbstractEvolutionStrategy, StrategyEvaluationResult

    class CustomStrategy(AbstractEvolutionStrategy):
        def __init__(self):
            super().__init__(strategy_id="CustomTestStrategy")
        def evaluate(self, context):
            return StrategyEvaluationResult()

    custom = CustomStrategy()
    registry.register(custom)
    assert registry.get("CustomTestStrategy") == custom

    registry.unregister("CustomTestStrategy")
    assert registry.get("CustomTestStrategy") is None
