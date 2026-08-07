"""
Unit tests for Resolution Rules, Plugins, and Registry.
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import (
    IntentConflictType,
    IntentDependencyType,
    IntentNode,
    IntentRelationshipType,
    IntentResolutionGraph,
)
from app.domain.intents.resolution.plugins.cross_industry import CrossIndustryResolutionPlugin
from app.domain.intents.resolution.plugins.healthcare import HealthcareResolutionPlugin
from app.domain.intents.resolution.plugins.real_estate import RealEstateResolutionPlugin
from app.domain.intents.resolution.registry import IntentResolutionRegistry
from app.domain.intents.resolution.rules.conflict_rules import (
    ContradictingIntentRule,
    DuplicateIntentRule,
    MutuallyExclusiveIntentRule,
    TimelineStateConflictRule,
)
from app.domain.intents.resolution.rules.dependency_rules import (
    BlockingSupportRule,
    PrerequisiteInquiryRule,
    SequentialRequirementRule,
)
from app.domain.intents.resolution.rules.relationship_rules import (
    ComplementaryCommercialRule,
    CrossIntentRelatedRule,
    SupportOperationalRule,
    TaxonomyHierarchyRelationshipRule,
)


def make_node(name: str, category: str = "GENERAL", path: str = "", state: str = "ACTIVE") -> IntentNode:
    return IntentNode(
        intent_id=uuid.uuid4(),
        canonical_name=name,
        raw_intent_type=name,
        category=category,
        taxonomy_path=path,
        confidence=0.9,
        lifecycle_state=state,
    )


def test_taxonomy_hierarchy_relationship_rule():
    rule = TaxonomyHierarchyRelationshipRule()
    parent = make_node("Billing", category="FINANCE", path="billing")
    child = make_node("UpdatePaymentMethod", category="FINANCE", path="billing.payment_method")

    graph = IntentResolutionGraph(nodes={str(parent.intent_id): parent, str(child.intent_id): child})
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    relationships = rule.evaluate_relationships([parent, child], graph, ctx)
    assert len(relationships) == 2
    types = {r.relationship_type for r in relationships}
    assert IntentRelationshipType.PARENT in types
    assert IntentRelationshipType.CHILD in types


def test_complementary_commercial_rule():
    rule = ComplementaryCommercialRule()
    demo_node = make_node("Schedule_Demo", category="COMMERCIAL")
    pricing_node = make_node("Request_Pricing", category="COMMERCIAL")

    graph = IntentResolutionGraph(nodes={str(demo_node.intent_id): demo_node, str(pricing_node.intent_id): pricing_node})
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    relationships = rule.evaluate_relationships([demo_node, pricing_node], graph, ctx)
    assert len(relationships) >= 1
    assert relationships[0].relationship_type == IntentRelationshipType.COMPLEMENTARY


def test_duplicate_intent_rule():
    rule = DuplicateIntentRule()
    n1 = make_node("Pricing_Inquiry", category="COMMERCIAL")
    n2 = make_node("Pricing_Inquiry", category="COMMERCIAL")

    graph = IntentResolutionGraph(nodes={str(n1.intent_id): n1, str(n2.intent_id): n2})
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    conflicts = rule.evaluate_conflicts([n1, n2], graph, ctx)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == IntentConflictType.DUPLICATE
    assert set(conflicts[0].intent_ids) == {n1.intent_id, n2.intent_id}


def test_mutually_exclusive_intent_rule():
    rule = MutuallyExclusiveIntentRule()
    n_buy = make_node("Purchase_Subscription", category="COMMERCIAL")
    n_cancel = make_node("Cancel_Account", category="COMMERCIAL")

    graph = IntentResolutionGraph(nodes={str(n_buy.intent_id): n_buy, str(n_cancel.intent_id): n_cancel})
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    conflicts = rule.evaluate_conflicts([n_buy, n_cancel], graph, ctx)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == IntentConflictType.MUTUALLY_EXCLUSIVE


def test_sequential_requirement_dependency_rule():
    rule = SequentialRequirementRule()
    n_auth = make_node("Verify_Identity_KYC", category="OPERATIONAL")
    n_change = make_node("Transfer_Funds_Payout", category="OPERATIONAL")

    graph = IntentResolutionGraph(nodes={str(n_auth.intent_id): n_auth, str(n_change.intent_id): n_change})
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    deps = rule.evaluate_dependencies([n_auth, n_change], graph, ctx)
    assert len(deps) == 1
    assert deps[0].dependency_type == IntentDependencyType.REQUIRED
    assert deps[0].source_intent_id == n_auth.intent_id
    assert deps[0].target_intent_id == n_change.intent_id
    assert deps[0].is_blocking is True


def test_blocking_support_dependency_rule():
    rule = BlockingSupportRule()
    n_bug = make_node("System_Outage_Critical_Bug", category="OPERATIONAL")
    n_upgrade = make_node("Upgrade_Enterprise_Plan", category="COMMERCIAL")

    graph = IntentResolutionGraph(nodes={str(n_bug.intent_id): n_bug, str(n_upgrade.intent_id): n_upgrade})
    ctx = MultiIntentResolutionContext(conversation_id="c1", entity_id="e1")

    deps = rule.evaluate_dependencies([n_bug, n_upgrade], graph, ctx)
    assert len(deps) == 1
    assert deps[0].dependency_type == IntentDependencyType.BLOCKING
    assert deps[0].is_blocking is True


def test_registry_and_industry_plugins():
    registry = IntentResolutionRegistry()

    plugins = registry.list_registered_plugins()
    assert "CrossIndustryResolutionPlugin" in plugins
    assert "RealEstateResolutionPlugin" in plugins
    assert "HealthcareResolutionPlugin" in plugins

    rules = registry.list_registered_rules()
    assert len(rules["relationship_rules"]) >= 4
    assert len(rules["conflict_rules"]) >= 4
    assert len(rules["dependency_rules"]) >= 3
    assert len(rules["dominance_strategies"]) >= 4

    # Test domain filtering
    re_deps = registry.get_dependency_rules(domain="REAL_ESTATE")
    assert any("RealEstate" in r.rule_name for r in re_deps)

    hc_conflicts = registry.get_conflict_rules(domain="HEALTHCARE")
    assert any("Healthcare" in r.rule_name for r in hc_conflicts)
