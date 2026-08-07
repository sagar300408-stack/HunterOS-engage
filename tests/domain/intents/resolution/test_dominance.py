"""
Unit tests for Dominance Strategies and Composite Engine.
"""

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.dominance.commercial import CommercialImportanceStrategy
from app.domain.intents.resolution.dominance.composite import CompositeDominanceStrategy
from app.domain.intents.resolution.dominance.evidence_coverage import EvidenceCoverageStrategy
from app.domain.intents.resolution.dominance.frequency import FrequencyStrategy
from app.domain.intents.resolution.dominance.persistence import PersistenceStrategy
from app.domain.intents.resolution.models import DominanceFactor, IntentNode


def create_sample_node(
    name: str,
    evidence_count: int = 1,
    evidence_msgs: list = None,
    importance: str = "NORMAL",
    category: str = "GENERAL",
    lifecycle: str = "ACTIVE",
    convs: list = None,
    span_days: int = 1,
) -> IntentNode:
    now = datetime.now(timezone.utc)
    return IntentNode(
        intent_id=uuid.uuid4(),
        canonical_name=name,
        raw_intent_type=name,
        category=category,
        confidence=0.9,
        business_importance=importance,
        lifecycle_state=lifecycle,
        source_conversations=convs or ["conv_1"],
        evidence_count=evidence_count,
        evidence_message_ids=evidence_msgs or [f"msg_{i}" for i in range(evidence_count)],
        first_seen=now - timedelta(days=span_days),
        last_seen=now,
    )


def test_evidence_coverage_strategy():
    strategy = EvidenceCoverageStrategy(weight=1.0)
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    node_low = create_sample_node("LowEvidence", evidence_count=2)
    node_high = create_sample_node("HighEvidence", evidence_count=10)

    res = strategy.evaluate([node_low, node_high], ctx)
    assert len(res) == 2
    assert res[node_high.intent_id].score > res[node_low.intent_id].score
    assert res[node_high.intent_id].factor == DominanceFactor.EVIDENCE_COVERAGE


def test_commercial_importance_strategy():
    strategy = CommercialImportanceStrategy(weight=1.0)
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    node_crit = create_sample_node("CritCommercial", importance="CRITICAL", category="COMMERCIAL")
    node_low = create_sample_node("LowInfo", importance="LOW", category="INFORMATION")

    res = strategy.evaluate([node_crit, node_low], ctx)
    assert res[node_crit.intent_id].score > res[node_low.intent_id].score
    assert res[node_crit.intent_id].score == 1.0


def test_persistence_strategy():
    strategy = PersistenceStrategy(weight=1.0)
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    node_persisting = create_sample_node("PersistNode", lifecycle="PERSISTING", span_days=10)
    node_transient = create_sample_node("TransientNode", lifecycle="WEAKENING", span_days=0)

    res = strategy.evaluate([node_persisting, node_transient], ctx)
    assert res[node_persisting.intent_id].score > res[node_transient.intent_id].score


def test_frequency_strategy():
    strategy = FrequencyStrategy(weight=1.0)
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    node_freq = create_sample_node("FreqNode", convs=["c1", "c2", "c3", "c4"])
    node_rare = create_sample_node("RareNode", convs=["c1"])

    res = strategy.evaluate([node_freq, node_rare], ctx)
    assert res[node_freq.intent_id].score > res[node_rare.intent_id].score


def test_composite_dominance_single_node():
    engine = CompositeDominanceStrategy()
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    node = create_sample_node("SoleIntent")
    dominant = engine.resolve_dominant_intent([node], ctx)

    assert dominant is not None
    assert dominant.intent_id == node.intent_id
    assert dominant.canonical_name == "SoleIntent"
    assert dominant.dominance_score == 1.0
    assert dominant.supporting_intent_ids == []


def test_composite_dominance_multi_node():
    engine = CompositeDominanceStrategy()
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    node_leader = create_sample_node(
        "LeaderIntent",
        evidence_count=15,
        importance="CRITICAL",
        category="COMMERCIAL",
        lifecycle="STRENGTHENING",
        convs=["c1", "c2", "c3"],
    )
    node_follower = create_sample_node(
        "FollowerIntent",
        evidence_count=2,
        importance="LOW",
        category="INFORMATION",
        lifecycle="NEW",
        convs=["c1"],
    )

    dominant = engine.resolve_dominant_intent([node_leader, node_follower], ctx)
    assert dominant is not None
    assert dominant.intent_id == node_leader.intent_id
    assert dominant.canonical_name == "LeaderIntent"
    assert dominant.dominance_score > 0.8
    assert node_follower.intent_id in dominant.supporting_intent_ids
