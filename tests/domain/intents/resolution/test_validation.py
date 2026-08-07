"""
Unit tests for Resolution Validation Guardrails.
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import (
    DominanceFactor,
    DominantIntent,
    IntentConflict,
    IntentConflictSeverity,
    IntentConflictType,
    IntentDependency,
    IntentDependencyType,
    IntentNode,
    IntentRelationship,
    IntentRelationshipType,
    IntentResolutionGraph,
    IntentResolutionGroup,
    ResolutionStatus,
)
from app.domain.intents.resolution.validation import MultiIntentResolutionValidator


def test_validator_clean_context():
    validator = MultiIntentResolutionValidator()
    ctx = MultiIntentResolutionContext(conversation_id="conv_1", entity_id="ent_1")

    node = IntentNode(
        intent_id=uuid.uuid4(),
        canonical_name="Pricing",
        raw_intent_type="Pricing",
        confidence=0.95,
    )
    ctx.normalized_nodes = {str(node.intent_id): node}
    ctx.resolution_graph = IntentResolutionGraph(nodes={str(node.intent_id): node})

    is_valid = validator.validate(ctx)
    assert is_valid is True
    assert len(ctx.validation_errors) == 0


def test_validator_cycle_detection():
    validator = MultiIntentResolutionValidator()
    ctx = MultiIntentResolutionContext(conversation_id="conv_1", entity_id="ent_1")

    id_a = uuid.uuid4()
    id_b = uuid.uuid4()

    node_a = IntentNode(intent_id=id_a, canonical_name="A", raw_intent_type="A", confidence=0.9)
    node_b = IntentNode(intent_id=id_b, canonical_name="B", raw_intent_type="B", confidence=0.9)

    ctx.normalized_nodes = {str(id_a): node_a, str(id_b): node_b}

    # Create cycle A -> B -> A
    dep1 = IntentDependency(
        dependency_type=IntentDependencyType.REQUIRED,
        source_intent_id=id_a,
        target_intent_id=id_b,
    )
    dep2 = IntentDependency(
        dependency_type=IntentDependencyType.REQUIRED,
        source_intent_id=id_b,
        target_intent_id=id_a,
    )

    ctx.analyzed_dependencies = [dep1, dep2]
    ctx.resolution_graph = IntentResolutionGraph(
        nodes=dict(ctx.normalized_nodes),
        dependencies=[dep1, dep2],
    )

    is_valid = validator.validate(ctx)
    assert is_valid is False
    assert any("cyclic" in err.lower() or "cycle" in err.lower() for err in ctx.validation_errors)


def test_validator_missing_node_references():
    validator = MultiIntentResolutionValidator()
    ctx = MultiIntentResolutionContext(conversation_id="conv_1", entity_id="ent_1")

    id_a = uuid.uuid4()
    id_ghost = uuid.uuid4()

    node_a = IntentNode(intent_id=id_a, canonical_name="A", raw_intent_type="A", confidence=0.9)
    ctx.normalized_nodes = {str(id_a): node_a}

    rel = IntentRelationship(
        source_intent_id=id_a,
        target_intent_id=id_ghost,
        relationship_type=IntentRelationshipType.RELATED,
    )
    ctx.analyzed_relationships = [rel]
    ctx.resolution_graph = IntentResolutionGraph(
        nodes=dict(ctx.normalized_nodes),
        edges=[rel],
    )

    is_valid = validator.validate(ctx)
    assert is_valid is False
    assert any(str(id_ghost) in err for err in ctx.validation_errors)
