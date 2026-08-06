"""
HunterOS Engage V1 - Sales Classification View
Commercial and deal-focused perspective for sales teams and pipeline managers.
"""

from __future__ import annotations

from typing import Any, Dict

from app.domain.intents.classification.models import (
    IntentCategory,
    IntentClassificationResult,
)
from app.domain.intents.classification.views.base import AbstractClassificationView


class SalesClassificationView(AbstractClassificationView):
    """
    Sales view filtering commercial, pricing, booking, and negotiation intents.
    """

    def __init__(self):
        super().__init__(
            view_name="SalesClassificationView",
            description="Sales view detailing commercial discussions, pricing inquiries, and booking interest.",
        )

    def generate(self, result: IntentClassificationResult) -> Dict[str, Any]:
        commercial_intents = [
            i for i in result.classified_intents
            if i.business_category == IntentCategory.COMMERCIAL
        ]
        info_intents = [
            i for i in result.classified_intents
            if i.business_category == IntentCategory.INFORMATION
        ]

        has_booking = any("booking_interest" in i.taxonomy_path.lower() for i in commercial_intents)
        has_negotiation = any("negotiation" in i.taxonomy_path.lower() for i in commercial_intents)
        has_pricing = any("pricing_inquiry" in i.taxonomy_path.lower() for i in commercial_intents)

        return {
            "view_type": "SALES",
            "conversation_id": result.conversation_id,
            "customer_id": result.customer_id,
            "commercial_signals": {
                "has_booking_intent": has_booking,
                "has_negotiation_intent": has_negotiation,
                "has_pricing_inquiry": has_pricing,
                "commercial_intent_count": len(commercial_intents),
                "inquiry_intent_count": len(info_intents),
            },
            "commercial_intents": [
                {
                    "intent_id": str(ci.classified_intent_id),
                    "taxonomy_path": ci.taxonomy_path,
                    "business_process": ci.business_process,
                    "confidence": ci.confidence,
                    "evidence_messages": ci.supporting_evidence.source_message_ids,
                    "snippets": ci.supporting_evidence.text_snippets,
                }
                for ci in commercial_intents
            ],
            "related_inquiries": [
                {
                    "intent_id": str(ci.classified_intent_id),
                    "taxonomy_path": ci.taxonomy_path,
                    "confidence": ci.confidence,
                }
                for ci in info_intents
            ],
        }
