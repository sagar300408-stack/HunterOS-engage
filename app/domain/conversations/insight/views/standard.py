"""
HunterOS Engage V1 - Standard Insight Views
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Standard perspective-specific projection views:
Executive, Sales, Operations, and Audit views.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.domain.conversations.insight.models import (
    ActionOwnerType,
    ConversationInsightResult,
    InsightPriority,
)
from app.domain.conversations.insight.views.base import AbstractInsightView
from app.domain.conversations.insight.views.registry import (
    InsightViewRegistry,
    default_insight_view_registry,
)


class ExecutiveInsightView(AbstractInsightView):
    """High-level executive briefing focusing on critical risks, top opportunities, and conversation health."""

    @property
    def view_name(self) -> str:
        return "executive"

    def render(self, result: ConversationInsightResult, **kwargs: Any) -> Dict[str, Any]:
        critical_risks = [r for r in result.risks if r.priority in (InsightPriority.CRITICAL, InsightPriority.HIGH)]
        high_opps = [o for o in result.opportunities if o.priority in (InsightPriority.CRITICAL, InsightPriority.HIGH)]
        urgent_actions = [a for a in result.action_items if a.priority in (InsightPriority.CRITICAL, InsightPriority.HIGH)]

        health_status = "HEALTHY"
        if any(r.priority == InsightPriority.CRITICAL for r in result.risks):
            health_status = "CRITICAL_ATTENTION_REQUIRED"
        elif critical_risks:
            health_status = "MONITORING_ADVISED"

        return {
            "view": "executive",
            "conversation_id": result.conversation_id,
            "workspace_id": str(result.workspace_id) if result.workspace_id else None,
            "health_status": health_status,
            "summary_metrics": {
                "total_insights": result.metadata.total_insights,
                "total_risks": result.metadata.total_risks,
                "critical_risks_count": len(critical_risks),
                "total_opportunities": result.metadata.total_opportunities,
                "high_value_opportunities_count": len(high_opps),
                "total_action_items": result.metadata.total_action_items,
                "urgent_actions_count": len(urgent_actions),
            },
            "critical_risk_alerts": [
                {
                    "risk_id": str(r.risk_id),
                    "category": r.category.value,
                    "title": r.title,
                    "description": r.description,
                    "impact": r.impact_description,
                    "priority": r.priority.value,
                }
                for r in critical_risks
            ],
            "high_value_opportunities": [
                {
                    "opportunity_id": str(o.opportunity_id),
                    "category": o.category.value,
                    "title": o.title,
                    "value_potential": o.value_potential,
                    "priority": o.priority.value,
                }
                for o in high_opps
            ],
            "immediate_action_items": [
                {
                    "action_id": str(a.action_id),
                    "category": a.category.value,
                    "owner_type": a.owner_type.value,
                    "title": a.title,
                    "due_date_hint": a.due_date_hint,
                    "priority": a.priority.value,
                }
                for a in urgent_actions
            ],
            "generated_at": result.metadata.generated_at.isoformat(),
        }


class SalesInsightView(AbstractInsightView):
    """Commercial focus highlighting qualification, upsell/cross-sell, budget indicators, and sales tasks."""

    @property
    def view_name(self) -> str:
        return "sales"

    def render(self, result: ConversationInsightResult, **kwargs: Any) -> Dict[str, Any]:
        sales_opp_cats = {"UPSELL", "CROSS_SELL", "QUALIFICATION", "MEETING"}
        commercial_opps = [o for o in result.opportunities if o.category.value in sales_opp_cats]
        budget_risks = [r for r in result.risks if r.category.value in ("BUDGET_GAP", "REQUIREMENT_AMBIGUITY")]
        sales_actions = [a for a in result.action_items if a.owner_type in (ActionOwnerType.INTERNAL_TEAM, ActionOwnerType.SHARED)]

        return {
            "view": "sales",
            "conversation_id": result.conversation_id,
            "commercial_opportunities": [
                {
                    "opportunity_id": str(o.opportunity_id),
                    "category": o.category.value,
                    "title": o.title,
                    "description": o.description,
                    "value_potential": o.value_potential,
                    "qualification_criteria": o.qualification_criteria,
                    "priority": o.priority.value,
                    "confidence": o.confidence,
                }
                for o in commercial_opps
            ],
            "budget_and_requirement_risks": [
                {
                    "risk_id": str(r.risk_id),
                    "category": r.category.value,
                    "title": r.title,
                    "description": r.description,
                    "priority": r.priority.value,
                }
                for r in budget_risks
            ],
            "sales_rep_action_items": [
                {
                    "action_id": str(a.action_id),
                    "category": a.category.value,
                    "title": a.title,
                    "description": a.description,
                    "due_date_hint": a.due_date_hint,
                    "priority": a.priority.value,
                }
                for a in sales_actions
            ],
        }


class OperationsInsightView(AbstractInsightView):
    """Operations focus emphasizing collateral dispatch, scheduled site visits, and pending customer actions."""

    @property
    def view_name(self) -> str:
        return "operations"

    def render(self, result: ConversationInsightResult, **kwargs: Any) -> Dict[str, Any]:
        doc_actions = [a for a in result.action_items if a.category.value == "REQUESTED_DOCUMENT"]
        scheduled_activities = [a for a in result.action_items if a.category.value == "SCHEDULED_ACTIVITY" or a.owner_type == ActionOwnerType.SHARED]
        customer_pending = [a for a in result.action_items if a.owner_type == ActionOwnerType.CUSTOMER]
        operational_risks = [r for r in result.risks if r.category.value in ("MISSING_DOCUMENT", "TIMELINE_CONFLICT", "MISSING_INFORMATION")]

        return {
            "view": "operations",
            "conversation_id": result.conversation_id,
            "document_fulfillment_queue": [
                {
                    "action_id": str(a.action_id),
                    "title": a.title,
                    "description": a.description,
                    "priority": a.priority.value,
                }
                for a in doc_actions
            ],
            "scheduled_calendar_activities": [
                {
                    "action_id": str(a.action_id),
                    "title": a.title,
                    "schedule_hint": a.due_date_hint,
                    "priority": a.priority.value,
                }
                for a in scheduled_activities
            ],
            "customer_pending_actions": [
                {
                    "action_id": str(a.action_id),
                    "title": a.title,
                    "description": a.description,
                    "due_date_hint": a.due_date_hint,
                }
                for a in customer_pending
            ],
            "operational_risks": [
                {
                    "risk_id": str(r.risk_id),
                    "category": r.category.value,
                    "title": r.title,
                    "description": r.description,
                }
                for r in operational_risks
            ],
        }


class AuditInsightView(AbstractInsightView):
    """Complete audit view showing every insight with granular evidence provenance."""

    @property
    def view_name(self) -> str:
        return "audit"

    def render(self, result: ConversationInsightResult, **kwargs: Any) -> Dict[str, Any]:
        insights_audit: List[Dict[str, Any]] = []

        for ins in result.all_insights:
            insights_audit.append(
                {
                    "insight_id": str(ins.insight_id),
                    "type": ins.insight_type.value,
                    "category": ins.category.value,
                    "title": ins.title,
                    "description": ins.description,
                    "priority": ins.priority.value,
                    "confidence": ins.confidence,
                    "evidence": {
                        "source_message_ids": ins.evidence.source_message_ids,
                        "source_event_ids": [str(eid) for eid in ins.evidence.source_event_ids],
                        "source_milestone_ids": [str(mid) for mid in ins.evidence.source_milestone_ids],
                        "source_moment_ids": [str(mom_id) for mom_id in ins.evidence.source_moment_ids],
                        "fact_ids": [str(fid) for fid in ins.evidence.fact_ids],
                        "topics": ins.evidence.topics,
                        "text_snippets": ins.evidence.text_snippets,
                        "extraction_method": ins.evidence.extraction_method,
                    },
                    "metadata": ins.metadata,
                    "created_at": ins.created_at.isoformat(),
                }
            )

        return {
            "view": "audit",
            "insight_result_id": str(result.insight_result_id),
            "conversation_id": result.conversation_id,
            "workspace_id": str(result.workspace_id) if result.workspace_id else None,
            "total_insights": len(insights_audit),
            "pipeline_diagnostics": {
                "execution_time_ms": result.diagnostics.pipeline_execution_time_ms,
                "stage_timings_ms": result.diagnostics.stage_timings_ms,
                "stages_executed": result.diagnostics.stages_executed,
                "warnings": result.diagnostics.warnings,
                "validation_errors": result.diagnostics.validation_errors,
                "is_valid": result.diagnostics.is_valid,
            },
            "insights": insights_audit,
            "schema_version": result.schema_version,
            "generator_version": result.generator_version,
        }


def register_standard_insight_views(registry: InsightViewRegistry) -> None:
    """Registers all standard insight projection views into the registry."""
    registry.register(ExecutiveInsightView())
    registry.register(SalesInsightView())
    registry.register(OperationsInsightView())
    registry.register(AuditInsightView())


# Populate default singleton registry
register_standard_insight_views(default_insight_view_registry)
