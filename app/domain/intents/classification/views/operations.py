"""
HunterOS Engage V1 - Operations Classification View
Operational execution and fulfillment perspective.
"""

from __future__ import annotations

from typing import Any, Dict

from app.domain.intents.classification.models import (
    IntentCategory,
    IntentClassificationResult,
    IntentRelationshipType,
)
from app.domain.intents.classification.views.base import AbstractClassificationView


class OperationsClassificationView(AbstractClassificationView):
    """
    Operations view focusing on site visits, meetings, document fulfillment, and logistical dependencies.
    """

    def __init__(self):
        super().__init__(
            view_name="OperationsClassificationView",
            description="Operations view detailing scheduling requests, document tasks, and workflow dependencies.",
        )

    def generate(self, result: IntentClassificationResult) -> Dict[str, Any]:
        op_intents = [
            i for i in result.classified_intents
            if i.business_category == IntentCategory.OPERATIONAL
        ]
        dep_relationships = [
            r for r in result.relationships
            if r.relationship_type == IntentRelationshipType.DEPENDENT_INTENT
        ]

        has_site_visit = any("site_visit" in i.taxonomy_path.lower() for i in op_intents)
        has_meeting = any("meeting_request" in i.taxonomy_path.lower() for i in op_intents)
        has_doc_request = any("document_request" in i.taxonomy_path.lower() for i in op_intents)

        return {
            "view_type": "OPERATIONS",
            "conversation_id": result.conversation_id,
            "operational_summary": {
                "total_operational_intents": len(op_intents),
                "has_site_visit": has_site_visit,
                "has_meeting_request": has_meeting,
                "has_document_request": has_doc_request,
                "total_dependencies": len(dep_relationships),
            },
            "operational_tasks": [
                {
                    "intent_id": str(ci.classified_intent_id),
                    "taxonomy_path": ci.taxonomy_path,
                    "business_process": ci.business_process,
                    "confidence": ci.confidence,
                    "snippets": ci.supporting_evidence.text_snippets,
                }
                for ci in op_intents
            ],
            "dependencies": [
                {
                    "relationship_id": str(r.relationship_id),
                    "source_intent_id": str(r.source_intent_id),
                    "target_intent_id": str(r.target_intent_id),
                    "reason": r.reason,
                    "confidence": r.confidence,
                }
                for r in dep_relationships
            ],
        }
