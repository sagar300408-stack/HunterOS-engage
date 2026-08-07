"""
HunterOS Engage V1 - Intent Resolution Registry
Central registry for pluggable industry plugins, rules, group builders, and dominance strategies.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.domain.intents.resolution.dominance.base import DominanceStrategy
from app.domain.intents.resolution.plugins.base import IndustryResolutionPlugin
from app.domain.intents.resolution.plugins.cross_industry import CrossIndustryResolutionPlugin
from app.domain.intents.resolution.plugins.healthcare import HealthcareResolutionPlugin
from app.domain.intents.resolution.plugins.real_estate import RealEstateResolutionPlugin
from app.domain.intents.resolution.rules.base import ConflictRule, DependencyRule, RelationshipRule


class IntentResolutionRegistry:
    """
    Registry for resolution plugins, rules, and dominance strategies.
    Thread-safe and deterministic.
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, IndustryResolutionPlugin] = {}
        self._relationship_rules: Dict[str, RelationshipRule] = {}
        self._conflict_rules: Dict[str, ConflictRule] = {}
        self._dependency_rules: Dict[str, DependencyRule] = {}
        self._dominance_strategies: Dict[str, DominanceStrategy] = {}

        # Register default industry plugins
        self._register_default_plugins()

    def _register_default_plugins(self) -> None:
        self.register_plugin(CrossIndustryResolutionPlugin())
        self.register_plugin(RealEstateResolutionPlugin())
        self.register_plugin(HealthcareResolutionPlugin())

    def register_plugin(self, plugin: IndustryResolutionPlugin) -> None:
        """Register an industry resolution plugin and its bundled rules & strategies."""
        self._plugins[plugin.plugin_name] = plugin

        for r_rule in plugin.get_relationship_rules():
            self.register_relationship_rule(r_rule)

        for c_rule in plugin.get_conflict_rules():
            self.register_conflict_rule(c_rule)

        for d_rule in plugin.get_dependency_rules():
            self.register_dependency_rule(d_rule)

        for d_strat in plugin.get_dominance_strategies():
            self.register_dominance_strategy(d_strat)

    def register_relationship_rule(self, rule: RelationshipRule) -> None:
        self._relationship_rules[rule.rule_name] = rule

    def register_conflict_rule(self, rule: ConflictRule) -> None:
        self._conflict_rules[rule.rule_name] = rule

    def register_dependency_rule(self, rule: DependencyRule) -> None:
        self._dependency_rules[rule.rule_name] = rule

    def register_dominance_strategy(self, strategy: DominanceStrategy) -> None:
        self._dominance_strategies[strategy.name] = strategy

    def get_plugin(self, plugin_name: str) -> Optional[IndustryResolutionPlugin]:
        return self._plugins.get(plugin_name)

    def get_relationship_rules(
        self,
        domain: Optional[str] = None,
        rule_pack_names: Optional[List[str]] = None,
    ) -> List[RelationshipRule]:
        rules = list(self._relationship_rules.values())
        if rule_pack_names:
            rules = [r for r in rules if r.rule_name in rule_pack_names]
        elif domain and domain != "CROSS_INDUSTRY":
            rules = [r for r in rules if r.domain in ("CROSS_INDUSTRY", domain)]
        return sorted(rules, key=lambda r: r.priority)

    def get_conflict_rules(
        self,
        domain: Optional[str] = None,
        rule_pack_names: Optional[List[str]] = None,
    ) -> List[ConflictRule]:
        rules = list(self._conflict_rules.values())
        if rule_pack_names:
            rules = [r for r in rules if r.rule_name in rule_pack_names]
        elif domain and domain != "CROSS_INDUSTRY":
            rules = [r for r in rules if r.domain in ("CROSS_INDUSTRY", domain)]
        return sorted(rules, key=lambda r: r.priority)

    def get_dependency_rules(
        self,
        domain: Optional[str] = None,
        rule_pack_names: Optional[List[str]] = None,
    ) -> List[DependencyRule]:
        rules = list(self._dependency_rules.values())
        if rule_pack_names:
            rules = [r for r in rules if r.rule_name in rule_pack_names]
        elif domain and domain != "CROSS_INDUSTRY":
            rules = [r for r in rules if r.domain in ("CROSS_INDUSTRY", domain)]
        return sorted(rules, key=lambda r: r.priority)

    def get_dominance_strategies(
        self,
        strategy_names: Optional[List[str]] = None,
    ) -> List[DominanceStrategy]:
        strategies = list(self._dominance_strategies.values())
        if strategy_names:
            strategies = [s for s in strategies if s.name in strategy_names]
        return strategies

    def list_registered_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def list_registered_rules(self) -> Dict[str, List[str]]:
        return {
            "relationship_rules": list(self._relationship_rules.keys()),
            "conflict_rules": list(self._conflict_rules.keys()),
            "dependency_rules": list(self._dependency_rules.keys()),
            "dominance_strategies": list(self._dominance_strategies.keys()),
        }


# Global Default Singleton Instance
default_resolution_registry = IntentResolutionRegistry()
