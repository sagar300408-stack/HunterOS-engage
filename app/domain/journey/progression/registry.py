"""
HunterOS Engage V1 — Stage Progression Rule Registry
Phase 2.4.2: Stage Progression Engine

Thread-safe registry for progression rules, organized by journey type and stage.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Set, Tuple

from app.domain.journey.models import JourneyStageCode, JourneyType
from app.domain.journey.progression.rules import (
    AbstractStageProgressionRule,
    DEFAULT_CROSS_INDUSTRY_RULES,
)


class StageProgressionRuleRegistry:
    """
    Thread-safe registry for stage progression rules.
    Rules are indexed by (journey_type, stage_code) for efficient lookup.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rules: List[AbstractStageProgressionRule] = []
        self._index: Dict[Tuple[str, str], List[AbstractStageProgressionRule]] = {}

    def register(self, rule: AbstractStageProgressionRule) -> None:
        """Register a progression rule."""
        with self._lock:
            self._rules.append(rule)
            self._rebuild_index()

    def register_many(self, rules: List[AbstractStageProgressionRule]) -> None:
        """Register multiple progression rules at once."""
        with self._lock:
            self._rules.extend(rules)
            self._rebuild_index()

    def get_rules_for_stage(
        self,
        journey_type: JourneyType,
        current_stage: JourneyStageCode,
    ) -> List[AbstractStageProgressionRule]:
        """Get all rules applicable to a given journey type and current stage."""
        with self._lock:
            key = (journey_type.value, current_stage.value)
            return list(self._index.get(key, []))

    def get_all_rules(self) -> List[AbstractStageProgressionRule]:
        """Get all registered rules."""
        with self._lock:
            return list(self._rules)

    def get_rules_by_name(self, rule_name: str) -> List[AbstractStageProgressionRule]:
        """Get rules matching a specific name."""
        with self._lock:
            return [r for r in self._rules if r.rule_name == rule_name]

    def list_rule_names(self) -> List[str]:
        """List all registered rule names."""
        with self._lock:
            return list(set(r.rule_name for r in self._rules))

    def exists(self, rule_name: str) -> bool:
        """Check if a rule with the given name is registered."""
        with self._lock:
            return any(r.rule_name == rule_name for r in self._rules)

    def remove(self, rule_name: str) -> bool:
        """Remove all rules with the given name. Returns True if any removed."""
        with self._lock:
            original_count = len(self._rules)
            self._rules = [r for r in self._rules if r.rule_name != rule_name]
            if len(self._rules) < original_count:
                self._rebuild_index()
                return True
            return False

    def clear(self) -> None:
        """Remove all registered rules."""
        with self._lock:
            self._rules.clear()
            self._index.clear()

    def _rebuild_index(self) -> None:
        """Rebuild the (journey_type, stage) -> rules index."""
        self._index.clear()
        for rule in self._rules:
            for jt in rule.supported_journey_types:
                if rule.supported_stages:
                    for stage in rule.supported_stages:
                        key = (jt.value, stage.value)
                        if key not in self._index:
                            self._index[key] = []
                        self._index[key].append(rule)
                else:
                    # Rules with empty supported_stages (e.g., initialization rules)
                    # are indexed under a special key
                    key = (jt.value, "__INIT__")
                    if key not in self._index:
                        self._index[key] = []
                    self._index[key].append(rule)


def create_default_rule_registry() -> StageProgressionRuleRegistry:
    """Create a registry pre-loaded with all cross-industry rules."""
    registry = StageProgressionRuleRegistry()
    registry.register_many(DEFAULT_CROSS_INDUSTRY_RULES)
    return registry


default_rule_registry: StageProgressionRuleRegistry = create_default_rule_registry()
