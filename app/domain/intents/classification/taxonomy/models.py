"""
HunterOS Engage V1 - Taxonomy Graph Data Models
Graph nodes, edges, and path representations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)


class TaxonomyNode(BaseModel):
    """
    A single classification node in the taxonomy graph.
    Nodes can have multiple parents and belong to cross-cutting categories.
    """
    model_config = ConfigDict(frozen=True)

    node_id: str
    category: IntentCategory
    display_name: str
    description: str = ""
    business_domain: BusinessDomain = BusinessDomain.CROSS_INDUSTRY
    default_process: str = "GENERAL_DISCOVERY"
    aliases: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "category": self.category.value,
            "display_name": self.display_name,
            "description": self.description,
            "business_domain": self.business_domain.value,
            "default_process": self.default_process,
            "aliases": self.aliases,
            "metadata": self.metadata,
        }


class TaxonomyEdge(BaseModel):
    """
    Directed relationship between taxonomy nodes (e.g. PARENT_OF, CROSS_LINK).
    """
    model_config = ConfigDict(frozen=True)

    source_node_id: str
    target_node_id: str
    relation: str = "PARENT_OF"
    weight: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relation": self.relation,
            "weight": self.weight,
            "metadata": self.metadata,
        }


class TaxonomyPath(BaseModel):
    """
    Hierarchical trace through the taxonomy graph from root to node.
    """
    model_config = ConfigDict(frozen=True, extra="allow")

    path_str: str = ""
    node_ids: List[str] = Field(default_factory=list)
    length: int = 0
    l1: Optional[str] = None
    l2: Optional[str] = None
    l3: Optional[str] = None
    l4: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            l1 = data.get("l1")
            l2 = data.get("l2")
            l3 = data.get("l3")
            l4 = data.get("l4")
            levels = [lvl for lvl in [l1, l2, l3, l4] if lvl is not None]

            node_ids = data.get("node_ids") or levels
            path_str = data.get("path_str") or " > ".join(str(x) for x in node_ids)
            length = data.get("length", len(node_ids))

            data["node_ids"] = node_ids
            data["path_str"] = path_str
            data["length"] = length
        return data

    @classmethod
    def from_nodes(cls, node_ids: List[str]) -> TaxonomyPath:
        path_str = " > ".join(node_ids)
        return cls(path_str=path_str, node_ids=node_ids, length=len(node_ids))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_str": self.path_str,
            "node_ids": self.node_ids,
            "length": self.length,
            "l1": self.l1,
            "l2": self.l2,
            "l3": self.l3,
            "l4": self.l4,
        }


TaxonomyNode.model_rebuild()
TaxonomyEdge.model_rebuild()
TaxonomyPath.model_rebuild()
