"""
HunterOS Engage — Context Export Engine (Phase 2.1.5)

Transforms a ComposedContext into multi-target serialization formats:
- Standard API DTOs
- Executive High-Level Summary DTOs
- Dashboard Frontend Card DTOs
- StructuredContextDTO (General-purpose structured context consumable by AI, analytics, or external systems)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.domain.memory.intelligence.models import (
    ComposedContext,
    ContextBlockType,
    ContextScope,
    ExportTargetFormat,
)
from app.domain.memory.intelligence.schemas import (
    ContextCompletenessResponse,
    ContextLineageResponse,
    ContextMetadataResponse,
    DashboardContextExportDTO,
    ExecutiveContextExportDTO,
    StructuredContextDTO,
)


class ContextExportEngine:
    """
    Serializes ComposedContext instances into structured export models.
    """

    def export(
        self,
        context: ComposedContext,
        target_format: ExportTargetFormat = ExportTargetFormat.STANDARD_API,
    ) -> Any:
        """Route to appropriate exporter."""
        if target_format == ExportTargetFormat.EXECUTIVE:
            return self.to_executive(context)
        elif target_format == ExportTargetFormat.DASHBOARD:
            return self.to_dashboard(context)
        elif target_format == ExportTargetFormat.STRUCTURED_CONTEXT:
            return self.to_structured_context(context)
        else:
            return self.to_standard_api(context)

    def to_standard_api(self, context: ComposedContext) -> Dict[str, Any]:
        """Convert to canonical dictionary payload."""
        return context.to_dict()

    def to_executive(self, context: ComposedContext) -> ExecutiveContextExportDTO:
        """Generate high-altitude executive summary."""
        scope_str = context.scope.value
        mem_block = context.get_block_data(ContextBlockType.MEMORY)
        rel_block = context.get_block_data(ContextBlockType.RELATIONSHIPS)
        stats_block = context.get_block_data(ContextBlockType.STATISTICS)

        overview: Dict[str, Any] = {
            "entity_id": context.entity_id,
            "scope": scope_str,
            "status": mem_block.get("lifecycle_status", "ACTIVE") if mem_block else "ACTIVE",
            "tier": mem_block.get("tier", "STANDARD") if mem_block else "STANDARD",
        }

        relationships_count = len(rel_block.get("items", [])) if "items" in rel_block else len(rel_block) if isinstance(rel_block, list) else 0

        key_metrics: Dict[str, Any] = {
            "total_relationships": relationships_count,
            "completeness_score": round(context.completeness.score, 4),
            "density": stats_block.get("density", 0.0),
            "connected_components": stats_block.get("connected_components", 1),
        }

        highlights: List[str] = [
            f"Context scope: {scope_str} for entity '{context.entity_id}'",
            f"Quality Completeness: {int(context.completeness.score * 100)}% ({context.completeness.status.value})",
            f"Network connections identified: {relationships_count}",
        ]

        if context.completeness.warnings:
            highlights.append(f"Diagnostics: {len(context.completeness.warnings)} validation notice(s)")

        return ExecutiveContextExportDTO(
            scope=scope_str,
            entity_id=context.entity_id,
            workspace_id=str(context.workspace_id) if context.workspace_id else None,
            overview=overview,
            key_metrics=key_metrics,
            highlights=highlights,
            completeness_score=context.completeness.score,
            generated_at=context.metadata.generated_at,
        )

    def to_dashboard(self, context: ComposedContext) -> DashboardContextExportDTO:
        """Generate frontend widget card payload."""
        cards: List[Dict[str, Any]] = []

        mem_block = context.get_block_data(ContextBlockType.MEMORY)
        if mem_block:
            cards.append({
                "id": "card-memory-core",
                "title": "Customer Profile",
                "type": "PROFILE_CARD",
                "data": mem_block,
            })

        rel_block = context.get_block_data(ContextBlockType.RELATIONSHIPS)
        rel_items = rel_block.get("items", []) if "items" in rel_block else rel_block if isinstance(rel_block, list) else []
        if rel_items:
            cards.append({
                "id": "card-relationships-network",
                "title": "Direct Relationships",
                "type": "NETWORK_CARD",
                "count": len(rel_items),
                "data": rel_items,
            })

        tl_block = context.get_block_data(ContextBlockType.TIMELINE)
        tl_items = tl_block.get("items", []) if "items" in tl_block else tl_block if isinstance(tl_block, list) else []

        stats_block = context.get_block_data(ContextBlockType.STATISTICS)
        network_summary = {
            "node_count": stats_block.get("total_nodes", len(rel_items) + 1 if rel_items else 1),
            "edge_count": stats_block.get("total_edges", len(rel_items)),
            "density": stats_block.get("density", 0.0),
        }

        completeness_dto = ContextCompletenessResponse(
            score=context.completeness.score,
            status=context.completeness.status,
            total_blocks_requested=context.completeness.total_blocks_requested,
            blocks_loaded=context.completeness.blocks_loaded,
            missing_fields=context.completeness.missing_fields,
            warnings=context.completeness.warnings,
            is_valid=context.completeness.is_valid,
        )

        return DashboardContextExportDTO(
            scope=context.scope.value,
            entity_id=context.entity_id,
            workspace_id=str(context.workspace_id) if context.workspace_id else None,
            cards=cards,
            network_summary=network_summary,
            timeline_preview=tl_items[:10] if isinstance(tl_items, list) else [],
            completeness=completeness_dto,
        )

    def to_structured_context(self, context: ComposedContext) -> StructuredContextDTO:
        """
        Generate general-purpose structured context format consumable by AI,
        analytics, or external systems without embedded inference.
        """
        mem_block = context.get_block_data(ContextBlockType.MEMORY)
        rel_block = context.get_block_data(ContextBlockType.RELATIONSHIPS)
        tl_block = context.get_block_data(ContextBlockType.TIMELINE)
        stats_block = context.get_block_data(ContextBlockType.STATISTICS)

        entity_key = f"{context.scope.value}:{context.entity_id or 'unknown'}"

        summary_sections: List[Dict[str, Any]] = []
        if mem_block:
            summary_sections.append({
                "header": "Core Profile",
                "attributes": {k: v for k, v in mem_block.items() if not isinstance(v, (dict, list))},
            })

        triplets: List[Dict[str, str]] = []
        rel_items = rel_block.get("items", []) if "items" in rel_block else rel_block if isinstance(rel_block, list) else []
        for r in rel_items:
            if isinstance(r, dict):
                s_key = r.get("source_node", {}).get("key") or f"{r.get('source_type')}:{r.get('source_id')}"
                t_key = r.get("target_node", {}).get("key") or f"{r.get('target_type')}:{r.get('target_id')}"
                r_type = r.get("relationship_type", "RELATED_TO")
                triplets.append({
                    "subject": str(s_key),
                    "predicate": str(r_type),
                    "object": str(t_key),
                    "strength": str(r.get("strength", 1.0)),
                })

        tl_items = tl_block.get("items", []) if "items" in tl_block else tl_block if isinstance(tl_block, list) else []
        chronological_events = tl_items if isinstance(tl_items, list) else []

        # Rough token estimate (chars / 4)
        approx_json = json.dumps(context.to_dict(), default=str)
        token_estimate = max(10, len(approx_json) // 4)

        lineage_dto = ContextLineageResponse(
            source_memory_ids=context.lineage.source_memory_ids,
            source_relationship_ids=context.lineage.source_relationship_ids,
            source_timeline_event_ids=context.lineage.source_timeline_event_ids,
            projections_applied=context.lineage.projections_applied,
            generated_at=context.lineage.generated_at,
            source_modules=context.lineage.source_modules,
            details=context.lineage.details,
        )

        completeness_dto = ContextCompletenessResponse(
            score=context.completeness.score,
            status=context.completeness.status,
            total_blocks_requested=context.completeness.total_blocks_requested,
            blocks_loaded=context.completeness.blocks_loaded,
            missing_fields=context.completeness.missing_fields,
            warnings=context.completeness.warnings,
            is_valid=context.completeness.is_valid,
        )

        return StructuredContextDTO(
            context_id=context.metadata.context_id,
            schema_version=context.metadata.schema_version,
            scope=context.scope.value,
            entity_key=entity_key,
            workspace_id=str(context.workspace_id) if context.workspace_id else None,
            summary_sections=summary_sections,
            entity_properties=mem_block,
            relationship_triplets=triplets,
            chronological_events=chronological_events,
            metrics=stats_block,
            token_estimate=token_estimate,
            lineage=lineage_dto,
            completeness=completeness_dto,
        )


default_context_export_engine = ContextExportEngine()
