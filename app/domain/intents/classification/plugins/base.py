"""
HunterOS Engage V1 - Industry Intent Plugin Interface
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.intents.classification.models import BusinessDomain
from app.domain.intents.classification.process.models import BusinessProcessDefinition
from app.domain.intents.classification.relationships.rules import AbstractRelationshipRule
from app.domain.intents.classification.rules.base import AbstractClassificationRulePack
from app.domain.intents.classification.taxonomy.models import (
    TaxonomyEdge,
    TaxonomyNode,
)


class IndustryIntentPlugin(BaseModel):
    """
    Self-contained industry plugin encapsulating:
    - Taxonomy Nodes & Edges
    - Classification Rule Pack
    - Business Process Definitions
    - Relationship Rules
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    plugin_id: str
    name: str
    version: str = "1.0.0"
    description: str
    business_domain: BusinessDomain
    taxonomy_nodes: List[TaxonomyNode] = Field(default_factory=list)
    taxonomy_edges: List[TaxonomyEdge] = Field(default_factory=list)
    rule_pack: Optional[AbstractClassificationRulePack] = None
    business_processes: List[BusinessProcessDefinition] = Field(default_factory=list)
    relationship_rules: List[AbstractRelationshipRule] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "business_domain": self.business_domain.value,
            "total_taxonomy_nodes": len(self.taxonomy_nodes),
            "total_taxonomy_edges": len(self.taxonomy_edges),
            "has_rule_pack": self.rule_pack is not None,
            "total_processes": len(self.business_processes),
            "total_relationship_rules": len(self.relationship_rules),
            "metadata": self.metadata,
        }
