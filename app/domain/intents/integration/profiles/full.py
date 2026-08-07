"""
HunterOS Engage V1 - Full Composition Profile
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.integration.models import (
    AuditIntentContext,
    CompositionProfileType,
    ExecutiveIntentContext,
    IntentIntelligenceContext,
    OperationsIntentContext,
    SalesIntentContext,
)
from app.domain.intents.integration.profiles.base import CompositionProfile


class FullProfile(CompositionProfile):
    """
    Comprehensive composition profile assembling all 4 Intent Intelligence subsystems
    and constructing all CQRS role projections (Executive, Sales, Operations, Audit).
    """

    def __init__(self) -> None:
        super().__init__(
            profile_name="FullProfile",
            profile_type=CompositionProfileType.FULL,
            required_modules=["DETECTION", "CLASSIFICATION", "EVOLUTION", "RESOLUTION"],
            description="Complete intent intelligence context with all 4 phases and all CQRS role perspectives.",
        )

    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        # Build Executive View
        context.executive_view = self._build_executive_view(context)

        # Build Sales View
        context.sales_view = self._build_sales_view(context)

        # Build Operations View
        context.operations_view = self._build_operations_view(context)

        # Build Audit View
        context.audit_view = self._build_audit_view(context)

    def _build_executive_view(self, context: IntentIntelligenceContext) -> ExecutiveIntentContext:
        dominant_intents: List[Dict[str, Any]] = []
        strategic_focus: List[str] = []
        high_severity_conflicts: List[Dict[str, Any]] = []

        if context.resolution_result and context.resolution_result.resolved_groups:
            for grp in context.resolution_result.resolved_groups:
                if grp.dominant_intent:
                    dominant_intents.append({
                        "canonical_name": grp.dominant_intent.canonical_name,
                        "dominance_score": grp.dominant_intent.dominance_score,
                        "dominance_factors": [
                            f.factor_type.value if hasattr(f.factor_type, "value") else str(f.factor_type)
                            for f in getattr(grp.dominant_intent, "factors", [])
                        ],
                    })
                    strategic_focus.append(grp.dominant_intent.canonical_name)

        if context.resolution_result and context.resolution_result.resolution_graph:
            for c in context.resolution_result.resolution_graph.conflicts:
                sev = c.severity.value if hasattr(c.severity, "value") else str(c.severity)
                if sev in ("HIGH", "CRITICAL"):
                    high_severity_conflicts.append({
                        "conflict_type": c.conflict_type.value if hasattr(c.conflict_type, "value") else str(c.conflict_type),
                        "severity": sev,
                        "description": c.description,
                        "resolution_hint": c.resolution_hint,
                    })

        comm_score = 0.0
        if context.classification_result and context.classification_result.classified_intents:
            comm_intents = [
                c for c in context.classification_result.classified_intents
                if str(getattr(c, "business_category", "")).upper() in ("COMMERCIAL", "INTENTCATEGORY.COMMERCIAL")
            ]
            comm_score = min(1.0, len(comm_intents) * 0.35)

        summary_parts = []
        if dominant_intents:
            names = ", ".join(d["canonical_name"] for d in dominant_intents)
            summary_parts.append(f"Dominant customer motions: {names}.")
        if high_severity_conflicts:
            summary_parts.append(f"{len(high_severity_conflicts)} critical strategic friction points require attention.")
        else:
            summary_parts.append("No critical friction detected.")

        return ExecutiveIntentContext(
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            strategic_focus=list(set(strategic_focus)),
            dominant_intents=dominant_intents,
            commercial_intensity_score=round(comm_score, 2),
            strategic_friction_count=len(high_severity_conflicts),
            high_severity_conflicts=high_severity_conflicts,
            executive_summary=" ".join(summary_parts),
        )

    def _build_sales_view(self, context: IntentIntelligenceContext) -> SalesIntentContext:
        active_commercial: List[Dict[str, Any]] = []
        buying_signals: List[str] = []
        churn_signals: List[str] = []
        deal_blockers: List[Dict[str, Any]] = []
        buying_vs_churn: List[Dict[str, Any]] = []

        if context.detection_result and context.detection_result.detected_intents:
            for det in context.detection_result.detected_intents:
                name = det.intent_type.value if hasattr(det.intent_type, "value") else str(det.intent_type)
                cat = det.category.value if hasattr(det.category, "value") else str(det.category)
                if cat.upper() == "COMMERCIAL" or any(k in name.upper() for k in ("PRICING", "BUY", "DEMO", "MEETING", "PRODUCT")):
                    active_commercial.append({
                        "intent_id": str(det.intent_id),
                        "intent_name": name,
                        "confidence": det.confidence_score,
                    })
                    buying_signals.append(f"Active commercial intent: {name}")

        if context.resolution_result and context.resolution_result.resolution_graph:
            for c in context.resolution_result.resolution_graph.conflicts:
                desc = c.description.lower()
                if "cancel" in desc or "churn" in desc or "mutually exclusive" in desc:
                    churn_signals.append(c.description)
                    buying_vs_churn.append({
                        "conflict_id": str(c.conflict_id),
                        "description": c.description,
                        "resolution_hint": c.resolution_hint,
                    })

            for d in context.resolution_result.resolution_graph.dependencies:
                if d.is_blocking:
                    deal_blockers.append({
                        "dependency_id": str(d.dependency_id),
                        "reason": d.reason,
                    })

        return SalesIntentContext(
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            active_commercial_intents=active_commercial,
            buying_signals=buying_signals,
            deal_blockers=deal_blockers,
            churn_risk_signals=churn_signals,
            buying_vs_churn_conflicts=buying_vs_churn,
            dominant_motion=active_commercial[0]["intent_name"] if active_commercial else None,
            velocity_state="ACCELERATING" if len(buying_signals) > len(churn_signals) else "FRICTION",
            recommended_context_cues=[f"Customer expressed: {b}" for b in buying_signals[:3]],
        )

    def _build_operations_view(self, context: IntentIntelligenceContext) -> OperationsIntentContext:
        service_reqs: List[Dict[str, Any]] = []
        doc_reqs: List[Dict[str, Any]] = []
        cancel_reqs: List[Dict[str, Any]] = []
        exec_deps: List[Dict[str, Any]] = []
        blocking_deps: List[Dict[str, Any]] = []

        if context.detection_result and context.detection_result.detected_intents:
            for det in context.detection_result.detected_intents:
                name = det.intent_type.value if hasattr(det.intent_type, "value") else str(det.intent_type)
                if "DOCUMENT" in name.upper():
                    doc_reqs.append({"intent_id": str(det.intent_id), "name": name})
                elif "SUPPORT" in name.upper() or "SERVICE" in name.upper() or "COMPLAINT" in name.upper():
                    service_reqs.append({"intent_id": str(det.intent_id), "name": name})
                elif "CANCEL" in name.upper():
                    cancel_reqs.append({"intent_id": str(det.intent_id), "name": name})

        if context.resolution_result and context.resolution_result.resolution_graph:
            for d in context.resolution_result.resolution_graph.dependencies:
                dep_dict = {
                    "source": str(d.source_intent_id),
                    "target": str(d.target_intent_id),
                    "type": d.dependency_type.value if hasattr(d.dependency_type, "value") else str(d.dependency_type),
                    "is_blocking": d.is_blocking,
                    "reason": d.reason,
                }
                exec_deps.append(dep_dict)
                if d.is_blocking:
                    blocking_deps.append(dep_dict)

        return OperationsIntentContext(
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            service_requests=service_reqs,
            document_requests=doc_reqs,
            cancellation_requests=cancel_reqs,
            execution_dependencies=exec_deps,
            blocking_prerequisites=blocking_deps,
            operational_friction_count=len(cancel_reqs) + len(blocking_deps),
            unresolved_dependencies_count=len(blocking_deps),
        )

    def _build_audit_view(self, context: IntentIntelligenceContext) -> AuditIntentContext:
        rules_map: Dict[str, List[str]] = {}
        ev_map: Dict[str, List[str]] = {}

        if context.detection_result and hasattr(context.detection_result, "diagnostics"):
            rules_map["DETECTION"] = list(getattr(context.detection_result.diagnostics, "rules_executed", []))

        if context.classification_result and hasattr(context.classification_result, "provenance"):
            rules_map["CLASSIFICATION"] = ["ClassificationPipeline"]

        if context.resolution_result and hasattr(context.resolution_result, "provenance"):
            rules_map["RESOLUTION"] = list(getattr(context.resolution_result.provenance, "rules_evaluated", []))

        if context.detection_result and context.detection_result.detected_intents:
            for det in context.detection_result.detected_intents:
                ev_map[str(det.intent_id)] = det.supporting_evidence_message_ids or []

        return AuditIntentContext(
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            workspace_id=context.workspace_id,
            rules_fired_by_subsystem=rules_map,
            evidence_message_id_map=ev_map,
            provenance_chain=context.provenance,
            graph_snapshot={
                "node_count": len(context.context_graph.nodes),
                "link_count": len(context.context_graph.links),
            },
            validation_status={
                "is_valid": context.diagnostics.is_valid,
                "error_count": len(context.diagnostics.validation_errors),
                "warning_count": len(context.diagnostics.warnings),
            },
            evaluation_timings_ms=context.diagnostics.evaluation_timings_ms,
        )
