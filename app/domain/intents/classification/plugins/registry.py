"""
HunterOS Engage V1 - Industry Plugin Registry
Central coordinator for industry plugins.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from app.domain.intents.classification.plugins.base import IndustryIntentPlugin
from app.domain.intents.classification.plugins.packs.cross_industry import (
    create_cross_industry_plugin,
)
from app.domain.intents.classification.plugins.packs.healthcare import (
    create_healthcare_plugin,
)
from app.domain.intents.classification.plugins.packs.manufacturing import (
    create_manufacturing_plugin,
)
from app.domain.intents.classification.plugins.packs.real_estate import (
    create_real_estate_plugin,
)
from app.domain.intents.classification.process.registry import (
    BusinessProcessRegistry,
    default_business_process_registry,
)
from app.domain.intents.classification.relationships.registry import (
    IntentRelationshipRuleRegistry,
    default_relationship_rule_registry,
)
from app.domain.intents.classification.rules.registry import (
    ClassificationRuleRegistry,
    default_classification_rule_registry,
)
from app.domain.intents.classification.taxonomy.graph import (
    BusinessIntentTaxonomyGraph,
    default_taxonomy_graph,
)


class IndustryPluginRegistry:
    """
    Manages registration and atomic propagation of IndustryIntentPlugins into sub-registries.
    """

    def __init__(
        self,
        taxonomy_graph: Optional[BusinessIntentTaxonomyGraph] = None,
        rule_registry: Optional[ClassificationRuleRegistry] = None,
        process_registry: Optional[BusinessProcessRegistry] = None,
        relationship_registry: Optional[IntentRelationshipRuleRegistry] = None,
    ):
        self._lock = threading.RLock()
        self._plugins: Dict[str, IndustryIntentPlugin] = {}
        self._taxonomy_graph = taxonomy_graph or default_taxonomy_graph
        self._rule_registry = rule_registry or default_classification_rule_registry
        self._process_registry = process_registry or default_business_process_registry
        self._relationship_registry = relationship_registry or default_relationship_rule_registry
        self._initialize_defaults()

    def register_plugin(self, plugin: IndustryIntentPlugin) -> None:
        """Atomically registers an industry plugin into all component registries."""
        with self._lock:
            self._plugins[plugin.plugin_id] = plugin

            # 1. Register Taxonomy Nodes
            for node in plugin.taxonomy_nodes:
                self._taxonomy_graph.add_node(node)

            # 2. Register Taxonomy Edges
            for edge in plugin.taxonomy_edges:
                self._taxonomy_graph.add_edge(
                    source_node_id=edge.source_node_id,
                    target_node_id=edge.target_node_id,
                    relation=edge.relation,
                    weight=edge.weight,
                )

            # 3. Register Rule Pack
            if plugin.rule_pack:
                self._rule_registry.register_pack(plugin.rule_pack)

            # 4. Register Business Processes
            for proc in plugin.business_processes:
                self._process_registry.register(proc)

            # 5. Register Relationship Rules
            for r_rule in plugin.relationship_rules:
                self._relationship_registry.register(r_rule)

    def get_plugin(self, plugin_id: str) -> Optional[IndustryIntentPlugin]:
        """Look up plugin by ID."""
        with self._lock:
            return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[IndustryIntentPlugin]:
        """List all registered industry plugins."""
        with self._lock:
            return list(self._plugins.values())

    def _initialize_defaults(self) -> None:
        """Seed built-in industry plugins."""
        self.register_plugin(create_cross_industry_plugin())
        self.register_plugin(create_real_estate_plugin())
        self.register_plugin(create_healthcare_plugin())
        self.register_plugin(create_manufacturing_plugin())


default_industry_plugin_registry = IndustryPluginRegistry()
