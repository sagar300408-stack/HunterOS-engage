"""
HunterOS Engage V1 - Intent Export Engine
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Multi-format projection generator converting IntentIntelligenceContext aggregates
into standard downstream DTO representations (Dashboard, Executive, Structured, Standard API, Full).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.domain.intents.integration.models import IntentIntelligenceContext
from app.domain.intents.integration.schemas import (
    AuditIntentContextDTO,
    ContextCompletenessReportDTO,
    ContextDiagnosticsDTO,
    ContextGraphLinkDTO,
    ContextGraphNodeDTO,
    ContextMetadataDTO,
    ContextProvenanceDTO,
    CustomIntentContextDTO,
    DashboardIntentContextDTO,
    ExecutiveIntentContextDTO,
    ExecutiveIntentDTO,
    IntentContextAnalyticsDTO,
    IntentContextGraphDTO,
    IntentIntelligenceContextDTO,
    OperationsIntentContextDTO,
    SalesIntentContextDTO,
    StandardAPIIntentContextDTO,
    StructuredIntentContextDTO,
)

logger = logging.getLogger(__name__)


class IntentExportEngine:
    """
    Export Engine transforming unified intent context aggregates into specific downstream contracts.
    """

    def to_full_dto(self, context: IntentIntelligenceContext) -> IntentIntelligenceContextDTO:
        meta_dto = ContextMetadataDTO(
            context_id=context.metadata.context_id,
            conversation_id=context.metadata.conversation_id,
            entity_id=context.metadata.entity_id,
            workspace_id=context.metadata.workspace_id,
            schema_version=context.metadata.schema_version,
            context_version=context.metadata.context_version,
            composition_profile=context.metadata.composition_profile,
            source_modules=context.metadata.source_modules,
            created_at=context.metadata.created_at,
        )

        prov_dto = ContextProvenanceDTO(
            integration_version=context.provenance.integration_version,
            gateway_version=context.provenance.gateway_version,
            pipeline_version=context.provenance.pipeline_version,
            engine_version=context.provenance.engine_version,
            composition_profile=context.provenance.composition_profile,
            source_modules=context.provenance.source_modules,
            detection_provenance=context.provenance.detection_provenance,
            classification_provenance=context.provenance.classification_provenance,
            evolution_provenance=context.provenance.evolution_provenance,
            resolution_provenance=context.provenance.resolution_provenance,
            generated_at=context.provenance.generated_at,
        )

        diag_dto = ContextDiagnosticsDTO(
            is_valid=context.diagnostics.is_valid,
            warnings=context.diagnostics.warnings,
            validation_errors=context.diagnostics.validation_errors,
            evaluation_timings_ms=context.diagnostics.evaluation_timings_ms,
            total_duration_ms=context.diagnostics.total_duration_ms,
            artifacts_processed=context.diagnostics.artifacts_processed,
            rules_applied=context.diagnostics.rules_applied,
        )

        comp_dto = ContextCompletenessReportDTO(
            has_detection=context.completeness_report.has_detection,
            has_classification=context.completeness_report.has_classification,
            has_evolution=context.completeness_report.has_evolution,
            has_resolution=context.completeness_report.has_resolution,
            has_conversation_analysis=context.completeness_report.has_conversation_analysis,
            has_timeline=context.completeness_report.has_timeline,
            has_insights=context.completeness_report.has_insights,
            completeness_score=context.completeness_report.completeness_score,
            missing_modules=context.completeness_report.missing_modules,
            total_detected_intents=context.completeness_report.total_detected_intents,
            total_classified_intents=context.completeness_report.total_classified_intents,
            total_evolution_histories=context.completeness_report.total_evolution_histories,
            total_resolved_groups=context.completeness_report.total_resolved_groups,
            total_conflicts=context.completeness_report.total_conflicts,
            total_dependencies=context.completeness_report.total_dependencies,
        )

        ana_dto = IntentContextAnalyticsDTO(
            intent_coverage=context.analytics.intent_coverage,
            module_coverage=context.analytics.module_coverage,
            missing_modules=context.analytics.missing_modules,
            composition_size_bytes=context.analytics.composition_size_bytes,
            total_intent_count=context.analytics.total_intent_count,
            resolved_group_count=context.analytics.resolved_group_count,
            unresolved_conflict_count=context.analytics.unresolved_conflict_count,
            dominant_intents_count=context.analytics.dominant_intents_count,
            assembly_time_ms=context.analytics.assembly_time_ms,
            validation_summary=context.analytics.validation_summary,
        )

        graph_nodes = {
            k: ContextGraphNodeDTO(
                node_id=v.node_id,
                subsystem=v.subsystem,
                intent_name=v.intent_name,
                confidence=v.confidence,
                status=v.status,
                attributes=v.attributes,
                evidence_ids=v.evidence_ids,
            )
            for k, v in context.context_graph.nodes.items()
        }
        graph_links = [
            ContextGraphLinkDTO(
                link_id=l.link_id,
                source_node_id=l.source_node_id,
                target_node_id=l.target_node_id,
                link_type=l.link_type.value if hasattr(l.link_type, "value") else str(l.link_type),
                metadata=l.metadata,
            )
            for l in context.context_graph.links
        ]
        graph_dto = IntentContextGraphDTO(
            graph_id=context.context_graph.graph_id,
            node_count=len(graph_nodes),
            link_count=len(graph_links),
            nodes=graph_nodes,
            links=graph_links,
        )

        exec_dto = None
        if context.executive_view:
            exec_dto = ExecutiveIntentContextDTO(
                context_id=context.executive_view.context_id,
                conversation_id=context.executive_view.conversation_id,
                entity_id=context.executive_view.entity_id,
                strategic_focus=context.executive_view.strategic_focus,
                dominant_intents=context.executive_view.dominant_intents,
                commercial_intensity_score=context.executive_view.commercial_intensity_score,
                strategic_friction_count=context.executive_view.strategic_friction_count,
                high_severity_conflicts=context.executive_view.high_severity_conflicts,
                executive_summary=context.executive_view.executive_summary,
                generated_at=context.executive_view.generated_at,
            )

        sales_dto = None
        if context.sales_view:
            sales_dto = SalesIntentContextDTO(
                context_id=context.sales_view.context_id,
                conversation_id=context.sales_view.conversation_id,
                entity_id=context.sales_view.entity_id,
                active_commercial_intents=context.sales_view.active_commercial_intents,
                buying_signals=context.sales_view.buying_signals,
                deal_blockers=context.sales_view.deal_blockers,
                churn_risk_signals=context.sales_view.churn_risk_signals,
                buying_vs_churn_conflicts=context.sales_view.buying_vs_churn_conflicts,
                dominant_motion=context.sales_view.dominant_motion,
                velocity_state=context.sales_view.velocity_state,
                recommended_context_cues=context.sales_view.recommended_context_cues,
                generated_at=context.sales_view.generated_at,
            )

        ops_dto = None
        if context.operations_view:
            ops_dto = OperationsIntentContextDTO(
                context_id=context.operations_view.context_id,
                conversation_id=context.operations_view.conversation_id,
                entity_id=context.operations_view.entity_id,
                service_requests=context.operations_view.service_requests,
                document_requests=context.operations_view.document_requests,
                cancellation_requests=context.operations_view.cancellation_requests,
                execution_dependencies=context.operations_view.execution_dependencies,
                blocking_prerequisites=context.operations_view.blocking_prerequisites,
                operational_friction_count=context.operations_view.operational_friction_count,
                unresolved_dependencies_count=context.operations_view.unresolved_dependencies_count,
                generated_at=context.operations_view.generated_at,
            )

        audit_dto = None
        if context.audit_view:
            audit_dto = AuditIntentContextDTO(
                context_id=context.audit_view.context_id,
                conversation_id=context.audit_view.conversation_id,
                entity_id=context.audit_view.entity_id,
                workspace_id=context.audit_view.workspace_id,
                rules_fired_by_subsystem=context.audit_view.rules_fired_by_subsystem,
                evidence_message_id_map=context.audit_view.evidence_message_id_map,
                provenance_chain=prov_dto,
                graph_snapshot=context.audit_view.graph_snapshot,
                validation_status=context.audit_view.validation_status,
                evaluation_timings_ms=context.audit_view.evaluation_timings_ms,
                generated_at=context.audit_view.generated_at,
            )

        custom_dto = None
        if context.custom_view:
            custom_dto = CustomIntentContextDTO(
                context_id=context.custom_view.context_id,
                conversation_id=context.custom_view.conversation_id,
                entity_id=context.custom_view.entity_id,
                applied_filters=context.custom_view.applied_filters,
                filtered_intents=context.custom_view.filtered_intents,
                filtered_conflicts=context.custom_view.filtered_conflicts,
                filtered_dependencies=context.custom_view.filtered_dependencies,
                generated_at=context.custom_view.generated_at,
            )

        return IntentIntelligenceContextDTO(
            context_id=context.context_id,
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            workspace_id=context.workspace_id,
            composition_profile=context.metadata.composition_profile,
            metadata=meta_dto,
            provenance=prov_dto,
            diagnostics=diag_dto,
            completeness_report=comp_dto,
            analytics=ana_dto,
            context_graph=graph_dto,
            executive_view=exec_dto,
            sales_view=sales_dto,
            operations_view=ops_dto,
            audit_view=audit_dto,
            custom_view=custom_dto,
        )

    def to_dashboard_dto(self, context: IntentIntelligenceContext) -> DashboardIntentContextDTO:
        dominant_intents = []
        if context.resolution_result and context.resolution_result.resolved_groups:
            for grp in context.resolution_result.resolved_groups:
                if grp.dominant_intent:
                    dominant_intents.append({
                        "name": grp.dominant_intent.canonical_name,
                        "dominance_score": grp.dominant_intent.dominance_score,
                    })

        buying_signals = context.sales_view.buying_signals if context.sales_view else []
        risk_signals = context.sales_view.churn_risk_signals if context.sales_view else []
        exec_summary = context.executive_view.executive_summary if context.executive_view else "Context analyzed."

        friction_count = (
            context.executive_view.strategic_friction_count if context.executive_view
            else len(context.context_graph.get_conflicts("all"))
        )

        return DashboardIntentContextDTO(
            context_id=context.context_id,
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            dominant_intents=dominant_intents,
            total_intents_detected=context.completeness_report.total_detected_intents,
            friction_count=friction_count,
            unresolved_blockers_count=context.completeness_report.total_dependencies,
            completeness_score=context.completeness_report.completeness_score,
            buying_signals=buying_signals,
            risk_signals=risk_signals,
            executive_summary=exec_summary,
            generated_at=context.metadata.created_at,
        )

    def to_executive_dto(self, context: IntentIntelligenceContext) -> ExecutiveIntentDTO:
        comm_intensity = context.executive_view.commercial_intensity_score if context.executive_view else 0.0
        primary_objs = context.executive_view.strategic_focus if context.executive_view else []
        critical_risks = [c.get("description", "") for c in (context.executive_view.high_severity_conflicts if context.executive_view else [])]
        takeaway = context.executive_view.executive_summary if context.executive_view else "Executive review ready."

        return ExecutiveIntentDTO(
            context_id=context.context_id,
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            commercial_intensity=comm_intensity,
            primary_objectives=primary_objs,
            critical_risks=critical_risks,
            strategic_takeaway=takeaway,
            generated_at=context.metadata.created_at,
        )

    def to_structured_dto(self, context: IntentIntelligenceContext) -> StructuredIntentContextDTO:
        intents_by_stage = {
            "DETECTION": [
                {"id": str(d.intent_id), "type": d.intent_type.value if hasattr(d.intent_type, "value") else str(d.intent_type), "confidence": d.confidence_score}
                for d in (context.detection_result.detected_intents if context.detection_result else [])
            ],
            "CLASSIFICATION": [
                {"id": str(c.original_intent_id), "process": c.business_process, "domain": c.business_domain.value if hasattr(c.business_domain, "value") else str(c.business_domain)}
                for c in (context.classification_result.classified_intents if context.classification_result else [])
            ],
            "EVOLUTION": [
                {"id": str(e.intent_id), "state": e.current_state.value if hasattr(e.current_state, "value") else str(e.current_state), "turns": e.observation_count}
                for e in (context.evolution_result.intent_histories if context.evolution_result else [])
            ],
            "RESOLUTION": [
                {"group_id": str(g.group_id), "dominant": g.dominant_intent.canonical_name if g.dominant_intent else None}
                for g in (context.resolution_result.resolved_groups if context.resolution_result else [])
            ],
        }

        conflicts = [
            {"id": str(c.conflict_id), "desc": c.description, "severity": c.severity.value if hasattr(c.severity, "value") else str(c.severity)}
            for c in (context.resolution_result.resolution_graph.conflicts if context.resolution_result and context.resolution_result.resolution_graph else [])
        ]
        dependencies = [
            {"id": str(d.dependency_id), "is_blocking": d.is_blocking, "reason": d.reason}
            for d in (context.resolution_result.resolution_graph.dependencies if context.resolution_result and context.resolution_result.resolution_graph else [])
        ]
        dominance = [
            {"intent": g.dominant_intent.canonical_name, "score": g.dominant_intent.dominance_score}
            for g in (context.resolution_result.resolved_groups if context.resolution_result else [])
            if g.dominant_intent
        ]

        return StructuredIntentContextDTO(
            context_id=context.context_id,
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            intents_by_stage=intents_by_stage,
            graph_representation={
                "nodes": len(context.context_graph.nodes),
                "links": len(context.context_graph.links),
            },
            active_conflicts=conflicts,
            blocking_dependencies=dependencies,
            dominance_rankings=dominance,
            completeness=ContextCompletenessReportDTO(
                has_detection=context.completeness_report.has_detection,
                has_classification=context.completeness_report.has_classification,
                has_evolution=context.completeness_report.has_evolution,
                has_resolution=context.completeness_report.has_resolution,
                has_conversation_analysis=context.completeness_report.has_conversation_analysis,
                has_timeline=context.completeness_report.has_timeline,
                has_insights=context.completeness_report.has_insights,
                completeness_score=context.completeness_report.completeness_score,
                missing_modules=context.completeness_report.missing_modules,
                total_detected_intents=context.completeness_report.total_detected_intents,
                total_classified_intents=context.completeness_report.total_classified_intents,
                total_evolution_histories=context.completeness_report.total_evolution_histories,
                total_resolved_groups=context.completeness_report.total_resolved_groups,
                total_conflicts=context.completeness_report.total_conflicts,
                total_dependencies=context.completeness_report.total_dependencies,
            ),
        )

    def to_standard_api_dto(self, context: IntentIntelligenceContext) -> StandardAPIIntentContextDTO:
        full = self.to_full_dto(context)
        detected = [
            {"intent_id": str(d.intent_id), "intent_type": d.intent_type.value if hasattr(d.intent_type, "value") else str(d.intent_type), "confidence": d.confidence_score}
            for d in (context.detection_result.detected_intents if context.detection_result else [])
        ]
        classified = [
            {"intent_id": str(c.original_intent_id), "business_process": c.business_process, "domain": c.business_domain.value if hasattr(c.business_domain, "value") else str(c.business_domain)}
            for c in (context.classification_result.classified_intents if context.classification_result else [])
        ]
        histories = [
            {"intent_id": str(e.intent_id), "name": e.canonical_intent_name, "state": e.current_state.value if hasattr(e.current_state, "value") else str(e.current_state)}
            for e in (context.evolution_result.intent_histories if context.evolution_result else [])
        ]
        groups = [
            {"group_id": str(g.group_id), "name": g.name, "dominant_intent": g.dominant_intent.canonical_name if g.dominant_intent else None}
            for g in (context.resolution_result.resolved_groups if context.resolution_result else [])
        ]
        conflicts = [
            {"conflict_id": str(c.conflict_id), "description": c.description, "severity": c.severity.value if hasattr(c.severity, "value") else str(c.severity)}
            for c in (context.resolution_result.resolution_graph.conflicts if context.resolution_result and context.resolution_result.resolution_graph else [])
        ]
        dependencies = [
            {"dependency_id": str(d.dependency_id), "is_blocking": d.is_blocking, "reason": d.reason}
            for d in (context.resolution_result.resolution_graph.dependencies if context.resolution_result and context.resolution_result.resolution_graph else [])
        ]

        return StandardAPIIntentContextDTO(
            context_id=context.context_id,
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            workspace_id=context.workspace_id,
            composition_profile=context.metadata.composition_profile,
            detected_intents=detected,
            classified_intents=classified,
            intent_histories=histories,
            resolved_groups=groups,
            conflicts=conflicts,
            dependencies=dependencies,
            analytics=full.analytics,
            completeness=full.completeness_report,
            metadata=full.metadata,
            provenance=full.provenance,
        )
