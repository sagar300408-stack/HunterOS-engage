"""
HunterOS Engage V1 - Audit Resolution View
Full audit and governance view containing end-to-end provenance, diagnostics, and graph verification logs.
"""

from __future__ import annotations

from typing import Any, Dict

from app.domain.intents.resolution.models import MultiIntentResolutionResult
from app.domain.intents.resolution.views.base import BaseResolutionView


class AuditResolutionView(BaseResolutionView):
    """
    Renders deep compliance, diagnostic, and provenance logs for auditability.
    """

    def render(self, result: MultiIntentResolutionResult) -> Dict[str, Any]:
        return {
            "view_type": "AUDIT",
            "resolution_id": str(result.resolution_id),
            "entity_type": result.entity_type,
            "entity_id": result.entity_id,
            "workspace_id": str(result.workspace_id) if result.workspace_id else None,
            "conversation_id": result.conversation_id,
            "provenance": {
                "resolution_version": result.provenance.resolution_version,
                "graph_version": result.provenance.graph_version,
                "rule_pack_version": result.provenance.rule_pack_version,
                "pipeline_version": result.provenance.pipeline_version,
                "engine_version": result.provenance.engine_version,
                "rule_packs_applied": result.provenance.rule_packs_applied,
                "plugins_applied": result.provenance.plugins_applied,
                "generated_at": result.provenance.generated_at.isoformat(),
            },
            "diagnostics": {
                "pipeline_execution_time_ms": result.diagnostics.pipeline_execution_time_ms,
                "stage_timings_ms": result.diagnostics.stage_timings_ms,
                "stages_executed": result.diagnostics.stages_executed,
                "rules_evaluated": result.diagnostics.rules_evaluated,
                "strategies_evaluated": result.diagnostics.strategies_evaluated,
                "is_valid": result.diagnostics.is_valid,
                "validation_errors": result.diagnostics.validation_errors,
                "warnings": result.diagnostics.warnings,
            },
            "snapshot": {
                "snapshot_id": str(result.snapshot.graph_snapshot_id),
                "graph_version": result.snapshot.graph_version,
                "node_count": result.snapshot.node_count,
                "edge_count": result.snapshot.edge_count,
                "conflict_count": result.snapshot.conflict_count,
                "dependency_count": result.snapshot.dependency_count,
                "group_count": result.snapshot.group_count,
                "dominant_intent_count": result.snapshot.dominant_intent_count,
                "captured_at": result.snapshot.captured_at.isoformat(),
            },
            "detailed_conflicts": [
                {
                    "conflict_id": str(c.conflict_id),
                    "type": c.conflict_type.value,
                    "severity": c.severity.value,
                    "intents": [str(iid) for iid in c.intent_ids],
                    "evidence_ids": c.evidence_ids,
                    "rule_name": c.rule_name,
                }
                for c in result.resolution_graph.conflicts
            ],
            "detailed_dependencies": [
                {
                    "dependency_id": str(d.dependency_id),
                    "type": d.dependency_type.value,
                    "source": str(d.source_intent_id),
                    "target": str(d.target_intent_id),
                    "is_blocking": d.is_blocking,
                    "evidence_ids": d.evidence_ids,
                    "rule_name": d.rule_name,
                }
                for d in result.resolution_graph.dependencies
            ],
            "generated_at": result.generated_at.isoformat(),
        }
