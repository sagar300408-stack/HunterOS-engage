"""
HunterOS Engage V1 - Intent Relationship Subsystem
Evaluates descriptive, non-mutating links between classified intent nodes.
"""

from app.domain.intents.classification.relationships.engine import (
    IntentRelationshipEngine,
    default_relationship_engine,
)
from app.domain.intents.classification.relationships.registry import (
    IntentRelationshipRuleRegistry,
    default_relationship_rule_registry,
)
from app.domain.intents.classification.relationships.rules import (
    AbstractRelationshipRule,
    ComplementRule,
    ConflictRule,
    DependencyRule,
    HierarchyRule,
    RelatedRule,
)

__all__ = [
    "AbstractRelationshipRule",
    "DependencyRule",
    "ConflictRule",
    "ComplementRule",
    "HierarchyRule",
    "RelatedRule",
    "IntentRelationshipRuleRegistry",
    "default_relationship_rule_registry",
    "IntentRelationshipEngine",
    "default_relationship_engine",
]
