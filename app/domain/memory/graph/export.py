"""
HunterOS Engage — Graph Export & Visualization Serializers (Phase 2.1.4)

Serializes Knowledge Graph data into industry-standard visualization formats:
  - Cytoscape.js
  - D3.js (Force-Directed Graph)
  - ReactFlow
  - Tabular / Adjacency matrices
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from app.domain.memory.graph.models import EntityReference, RelationshipAggregate
from app.domain.memory.graph.schemas import VisualizationGraphDTO


class GraphExportEngine:
    """
    Serializes graph relationships into visualization-ready schemas.
    """

    @staticmethod
    def export_cytoscape(edges: List[RelationshipAggregate]) -> VisualizationGraphDTO:
        """Export in Cytoscape.js elements schema format."""
        nodes_map: Dict[str, EntityReference] = {}
        edge_elements: List[Dict[str, Any]] = []

        for edge in edges:
            nodes_map[edge.source.key] = edge.source
            nodes_map[edge.target.key] = edge.target

            rel_type = edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type)
            edge_elements.append({
                "data": {
                    "id": str(edge.id),
                    "source": edge.source.key,
                    "target": edge.target.key,
                    "label": rel_type,
                    "relationship_type": rel_type,
                    "strength": edge.strength,
                    "confidence": edge.metadata.confidence,
                    "direction": edge.direction.value if hasattr(edge.direction, "value") else str(edge.direction),
                    "status": edge.status.value if hasattr(edge.status, "value") else str(edge.status),
                }
            })

        node_elements = [
            {
                "data": {
                    "id": node.key,
                    "label": node.label or node.key,
                    "entity_type": node.entity_type.value if hasattr(node.entity_type, "value") else str(node.entity_type),
                    "entity_id": node.entity_id,
                    "properties": node.properties,
                }
            }
            for node in nodes_map.values()
        ]

        return VisualizationGraphDTO(
            format="cytoscape",
            nodes=node_elements,
            edges=edge_elements,
            metadata={"node_count": len(node_elements), "edge_count": len(edge_elements)},
        )

    @staticmethod
    def export_d3(edges: List[RelationshipAggregate]) -> VisualizationGraphDTO:
        """Export in D3 force-directed node-link schema format."""
        nodes_map: Dict[str, EntityReference] = {}
        links: List[Dict[str, Any]] = []

        for edge in edges:
            nodes_map[edge.source.key] = edge.source
            nodes_map[edge.target.key] = edge.target

            rel_type = edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type)
            links.append({
                "source": edge.source.key,
                "target": edge.target.key,
                "relationship_type": rel_type,
                "value": edge.strength,
                "confidence": edge.metadata.confidence,
            })

        nodes = [
            {
                "id": node.key,
                "name": node.label or node.key,
                "group": node.entity_type.value if hasattr(node.entity_type, "value") else str(node.entity_type),
                "properties": node.properties,
            }
            for node in nodes_map.values()
        ]

        return VisualizationGraphDTO(
            format="d3",
            nodes=nodes,
            edges=links,
            metadata={"node_count": len(nodes), "link_count": len(links)},
        )

    @staticmethod
    def export_reactflow(edges: List[RelationshipAggregate]) -> VisualizationGraphDTO:
        """Export in ReactFlow nodes and edges schema format."""
        nodes_map: Dict[str, EntityReference] = {}
        rf_edges: List[Dict[str, Any]] = []

        for edge in edges:
            nodes_map[edge.source.key] = edge.source
            nodes_map[edge.target.key] = edge.target

            rel_type = edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type)
            rf_edges.append({
                "id": str(edge.id),
                "source": edge.source.key,
                "target": edge.target.key,
                "label": rel_type,
                "animated": edge.strength >= 0.8,
                "data": {
                    "strength": edge.strength,
                    "confidence": edge.metadata.confidence,
                },
            })

        rf_nodes = [
            {
                "id": node.key,
                "type": "default",
                "data": {
                    "label": node.label or node.key,
                    "entityType": node.entity_type.value if hasattr(node.entity_type, "value") else str(node.entity_type),
                    "entityId": node.entity_id,
                },
                "position": {"x": 0, "y": 0},
            }
            for node in nodes_map.values()
        ]

        return VisualizationGraphDTO(
            format="reactflow",
            nodes=rf_nodes,
            edges=rf_edges,
            metadata={"node_count": len(rf_nodes), "edge_count": len(rf_edges)},
        )

    @staticmethod
    def export_tabular(edges: List[RelationshipAggregate]) -> List[Dict[str, Any]]:
        """Export as flat tabular rows for CSV / Excel export."""
        rows = []
        for edge in edges:
            rows.append({
                "relationship_id": str(edge.id),
                "workspace_id": str(edge.workspace_id) if edge.workspace_id else "",
                "source_type": edge.source.entity_type.value if hasattr(edge.source.entity_type, "value") else str(edge.source.entity_type),
                "source_id": edge.source.entity_id,
                "source_label": edge.source.label or "",
                "target_type": edge.target.entity_type.value if hasattr(edge.target.entity_type, "value") else str(edge.target.entity_type),
                "target_id": edge.target.entity_id,
                "target_label": edge.target.label or "",
                "relationship_type": edge.relationship_type.value if hasattr(edge.relationship_type, "value") else str(edge.relationship_type),
                "direction": edge.direction.value if hasattr(edge.direction, "value") else str(edge.direction),
                "strength": edge.strength,
                "confidence": edge.metadata.confidence,
                "source_system": edge.metadata.source,
                "status": edge.status.value if hasattr(edge.status, "value") else str(edge.status),
                "created_at": edge.created_at.isoformat(),
            })
        return rows


__all__ = [
    "GraphExportEngine",
]
