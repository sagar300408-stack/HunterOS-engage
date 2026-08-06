"""
HunterOS Engage V1 - Intent Relationship Rule Registry
Thread-safe registry for modular relationship inference rules.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from app.domain.intents.classification.relationships.rules import (
    AbstractRelationshipRule,
    ComplementRule,
    ConflictRule,
    DependencyRule,
    HierarchyRule,
    RelatedRule,
)


class IntentRelationshipRuleRegistry:
    """
    Registry managing extensible relationship evaluation rules.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._rules: Dict[str, AbstractRelationshipRule] = {}
        self._initialize_default_rules()

    def register(self, rule: AbstractRelationshipRule) -> None:
        """Register or replace a relationship rule."""
        with self._lock:
            self._rules[rule.rule_name] = rule

    def unregister(self, rule_name: str) -> Optional[AbstractRelationshipRule]:
        """Unregister a rule by name."""
        with self._lock:
            return self._rules.pop(rule_name, None)

    def get_rule(self, rule_name: str) -> Optional[AbstractRelationshipRule]:
        """Get rule instance by name."""
        with self._lock:
            return self._rules.get(rule_name)

    def list_rules(self) -> List[AbstractRelationshipRule]:
        """Return all registered relationship rules."""
        with self._lock:
            return list(self._rules.values())

    def _initialize_default_rules(self) -> None:
        """Seed default relationship rules."""
        self.register(DependencyRule(rule_version="1.0.0"))
        self.register(ConflictRule(rule_version="1.0.0"))
        self.register(ComplementRule(rule_version="1.0.0"))
        self.register(HierarchyRule(rule_version="1.0.0"))
        self.register(RelatedRule(rule_version="1.0.0"))


default_relationship_rule_registry = IntentRelationshipRuleRegistry()
