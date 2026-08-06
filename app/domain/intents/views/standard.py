"""
HunterOS Engage V1 - Standard Intent View Projections
Executive, Sales, Operations, and Audit perspective projections.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.domain.intents.models import (
    IntentDetectionResult,
    IntentTaxonomyCategory,
)
from app.domain.intents.views.base import AbstractIntentView


class ExecutiveIntentView(AbstractIntentView):
    """High-level summary of customer objectives for executive reporting."""

    @property
    def view_name(self) -> str:
        return "executive"

    @property
    def description(self) -> str:
        return "Executive summary of customer intents, category breakdown, and key objectives."

    def render(self, result: IntentDetectionResult) -> Dict[str, Any]:
        return {
            "view": self.view_name,
            "conversation_id": result.conversation_id,
            "customer_id": result.customer_id,
            "total_intents_detected": result.metadata.total_intents,
            "primary_intent": result.metadata.primary_intent.value if result.metadata.primary_intent else None,
            "dominant_category": result.metadata.dominant_category.value if result.metadata.dominant_category else None,
            "category_distribution": result.metadata.category_distribution,
            "average_confidence": result.metadata.average_confidence,
            "key_objectives": [
                {
                    "intent_type": i.intent_type.value,
                    "title": i.title,
                    "category": i.taxonomy_category.value,
                    "importance": i.business_importance.value,
                    "confidence": i.confidence,
                }
                for i in result.intents[:5]
            ],
            "detected_at": result.detected_at.isoformat(),
        }


class SalesIntentView(AbstractIntentView):
    """Commercial focus for sales reps and account executives."""

    @property
    def view_name(self) -> str:
        return "sales"

    @property
    def description(self) -> str:
        return "Commercial perspective focused on property inquiries, pricing, budget, and booking interest."

    def render(self, result: IntentDetectionResult) -> Dict[str, Any]:
        commercial_intents = [
            i for i in result.intents
            if i.taxonomy_category == IntentTaxonomyCategory.COMMERCIAL
            or i.intent_type.value in ("SCHEDULE_SITE_VISIT", "PROPOSAL_REQUEST")
        ]

        return {
            "view": self.view_name,
            "conversation_id": result.conversation_id,
            "customer_id": result.customer_id,
            "commercial_intent_count": len(commercial_intents),
            "commercial_intents": [
                {
                    "intent_id": str(i.intent_id),
                    "intent_type": i.intent_type.value,
                    "title": i.title,
                    "description": i.description,
                    "confidence": i.confidence,
                    "importance": i.business_importance.value,
                    "evidence_snippet": i.supporting_evidence.text_snippets[0] if i.supporting_evidence.text_snippets else None,
                }
                for i in commercial_intents
            ],
            "booking_interest_detected": any(i.intent_type.value == "BOOKING_INTEREST" for i in result.intents),
            "site_visit_requested": any(i.intent_type.value == "SCHEDULE_SITE_VISIT" for i in result.intents),
            "pricing_discussed": any(i.intent_type.value in ("PRICING_INQUIRY", "BUDGET_DISCUSSION") for i in result.intents),
            "negotiation_active": any(i.intent_type.value == "NEGOTIATION" for i in result.intents),
        }


class OperationsIntentView(AbstractIntentView):
    """Operational focus tracking service, support, documentation, and coordination."""

    @property
    def view_name(self) -> str:
        return "operations"

    @property
    def description(self) -> str:
        return "Operations perspective tracking support requests, document requirements, and meeting coordination."

    def render(self, result: IntentDetectionResult) -> Dict[str, Any]:
        operational_intents = [
            i for i in result.intents
            if i.taxonomy_category in (IntentTaxonomyCategory.OPERATIONAL, IntentTaxonomyCategory.RELATIONSHIP)
        ]

        return {
            "view": self.view_name,
            "conversation_id": result.conversation_id,
            "customer_id": result.customer_id,
            "operational_intents": [
                {
                    "intent_id": str(i.intent_id),
                    "intent_type": i.intent_type.value,
                    "title": i.title,
                    "description": i.description,
                    "category": i.taxonomy_category.value,
                    "importance": i.business_importance.value,
                    "confidence": i.confidence,
                    "source_messages": i.source_messages,
                }
                for i in operational_intents
            ],
            "document_requests": [
                i.title for i in result.intents if i.intent_type.value == "DOCUMENT_REQUEST"
            ],
            "complaints": [
                i.title for i in result.intents if i.intent_type.value == "COMPLAINT"
            ],
            "cancellations": [
                i.title for i in result.intents if i.intent_type.value == "CANCELLATION"
            ],
        }


class AuditIntentView(AbstractIntentView):
    """Comprehensive compliance and engineering audit trail."""

    @property
    def view_name(self) -> str:
        return "audit"

    @property
    def description(self) -> str:
        return "Complete audit projection with evidence graphs, lineage, and rule execution diagnostics."

    def render(self, result: IntentDetectionResult) -> Dict[str, Any]:
        return {
            "view": self.view_name,
            "detection_id": str(result.detection_id),
            "conversation_id": result.conversation_id,
            "workspace_id": str(result.workspace_id) if result.workspace_id else None,
            "customer_id": result.customer_id,
            "schema_version": result.schema_version,
            "detected_at": result.detected_at.isoformat(),
            "diagnostics": result.diagnostics.to_dict(),
            "intents": [i.to_dict() for i in result.intents],
        }
