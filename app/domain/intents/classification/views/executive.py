"""
HunterOS Engage V1 - Executive Classification View
High-level strategic perspective for leadership and overview dashboards.
"""

from __future__ import annotations

from typing import Any, Dict

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.classification.views.base import AbstractClassificationView


class ExecutiveClassificationView(AbstractClassificationView):
    """
    Executive view providing strategic domain distribution, high-level intent categories,
    and business process engagement metrics.
    """

    def __init__(self):
        super().__init__(
            view_name="ExecutiveClassificationView",
            description="Executive strategic view summarizing business category breakdown and process velocity.",
        )

    def generate(self, result: IntentClassificationResult) -> Dict[str, Any]:
        meta = result.metadata
        return {
            "view_type": "EXECUTIVE",
            "conversation_id": result.conversation_id,
            "workspace_id": str(result.workspace_id) if result.workspace_id else None,
            "customer_id": result.customer_id,
            "summary": {
                "total_intents_classified": meta.total_classified_intents,
                "primary_domain": meta.primary_domain.value if meta.primary_domain else "UNSPECIFIED",
                "primary_category": meta.primary_category.value if meta.primary_category else "UNSPECIFIED",
                "primary_business_process": meta.primary_process or "UNSPECIFIED",
                "total_intent_clusters": meta.total_groups,
                "total_structural_relationships": meta.total_relationships,
            },
            "category_breakdown": meta.category_distribution,
            "domain_breakdown": meta.domain_distribution,
            "clusters": [
                {
                    "group_id": str(g.group_id),
                    "name": g.name,
                    "group_type": g.group_type.value,
                    "intent_count": len(g.intent_ids),
                    "confidence": g.aggregate_confidence,
                }
                for g in result.groups
            ],
            "classification_version": meta.classification_version,
            "taxonomy_version": meta.taxonomy_version,
        }
