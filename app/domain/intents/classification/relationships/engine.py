"""
HunterOS Engage V1 - Intent Relationship Engine
Orchestrates relationship rule evaluations across classified intents.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
import uuid

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import IntentRelationship
from app.domain.intents.classification.relationships.registry import (
    IntentRelationshipRuleRegistry,
    default_relationship_rule_registry,
)


class IntentRelationshipEngine:
    """
    Evaluates relationship rules from the registry and builds a deduplicated, valid relationship graph.
    """

    def __init__(self, registry: Optional[IntentRelationshipRuleRegistry] = None):
        self._registry = registry or default_relationship_rule_registry

    def compute_relationships(self, context: IntentClassificationContext) -> List[IntentRelationship]:
        """
        Executes all active relationship rules and returns deduplicated relationships.
        """
        raw_relationships: List[IntentRelationship] = []
        rules = self._registry.list_rules()

        for rule in rules:
            try:
                results = rule.evaluate(context)
                raw_relationships.extend(results)
            except Exception as e:
                context.add_warning(f"Error evaluating relationship rule '{rule.rule_name}': {str(e)}")

        # Deduplicate & Filter Invalid Links
        unique_relationships: List[IntentRelationship] = []
        seen_keys: Set[Tuple[uuid.UUID, uuid.UUID, str]] = set()

        for rel in raw_relationships:
            # Self-reference filter
            if rel.source_intent_id == rel.target_intent_id:
                continue

            key = (rel.source_intent_id, rel.target_intent_id, rel.relationship_type.value)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_relationships.append(rel)

        return unique_relationships


default_relationship_engine = IntentRelationshipEngine()
