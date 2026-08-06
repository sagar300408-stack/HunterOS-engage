"""
HunterOS Engage V1 - Intent Grouping Engine
Clusters classified intents into structured functional groups.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional
import uuid

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    ClassifiedIntent,
    IntentCategory,
    IntentGroup,
    IntentGroupType,
)


class IntentGroupingEngine:
    """
    Groups classified intents into category-based and workflow-based clusters.
    """

    # Priority weighting for primary intent selection
    INTENT_PRIORITY_ORDER = [
        "booking_interest",
        "cancellation",
        "complaint",
        "pricing_inquiry",
        "site_visit",
        "meeting_request",
        "budget_discussion",
        "proposal_request",
        "document_request",
        "property_inquiry",
        "product_inquiry",
        "finance_inquiry",
        "referral",
        "partnership",
        "general_inquiry",
    ]

    def group_intents(self, context: IntentClassificationContext) -> List[IntentGroup]:
        """
        Partitions classified intents into IntentGroup entities.
        """
        intents = context.classified_intents
        if not intents:
            return []

        # 1. Bucket by business category
        category_buckets: Dict[IntentCategory, List[ClassifiedIntent]] = defaultdict(list)
        for intent in intents:
            category_buckets[intent.business_category].append(intent)

        groups: List[IntentGroup] = []

        category_meta = {
            IntentCategory.COMMERCIAL: (
                IntentGroupType.COMMERCIAL,
                "Commercial Intents Group",
                "Cluster of commercial, financial, pricing, and transactional intents.",
            ),
            IntentCategory.OPERATIONAL: (
                IntentGroupType.OPERATIONAL,
                "Operational Intents Group",
                "Cluster of scheduling, logistical, and document fulfillment intents.",
            ),
            IntentCategory.RELATIONSHIP: (
                IntentGroupType.RELATIONSHIP,
                "Relationship Intents Group",
                "Cluster of customer service, complaint, referral, and partnership intents.",
            ),
            IntentCategory.INFORMATION: (
                IntentGroupType.INFORMATION,
                "Information Intents Group",
                "Cluster of discovery, property search, and informational inquiries.",
            ),
            IntentCategory.CUSTOM: (
                IntentGroupType.CUSTOM,
                "Custom Intents Group",
                "Cluster of custom domain intents.",
            ),
        }

        for cat, bucket_intents in category_buckets.items():
            if not bucket_intents:
                continue

            g_type, default_name, default_desc = category_meta.get(
                cat,
                (IntentGroupType.CUSTOM, f"{cat.value} Group", f"Cluster of {cat.value} intents."),
            )

            primary_id = self._select_primary_intent(bucket_intents)
            avg_conf = sum(i.confidence for i in bucket_intents) / len(bucket_intents)

            groups.append(
                IntentGroup(
                    group_type=g_type,
                    name=default_name,
                    description=default_desc,
                    intent_ids=[i.classified_intent_id for i in bucket_intents],
                    primary_intent_id=primary_id,
                    aggregate_confidence=round(avg_conf, 4),
                    metadata={
                        "intent_count": len(bucket_intents),
                        "taxonomy_paths": [i.taxonomy_path for i in bucket_intents],
                    },
                )
            )

        return groups

    def _select_primary_intent(self, intents: List[ClassifiedIntent]) -> Optional[uuid.UUID]:
        """Picks the primary intent within a group based on priority weight and confidence."""
        if not intents:
            return None

        def _score(i: ClassifiedIntent) -> float:
            base_score = i.confidence
            for idx, p_key in enumerate(self.INTENT_PRIORITY_ORDER):
                if p_key in i.taxonomy_path.lower():
                    # Earlier in list has higher boost
                    return base_score + (len(self.INTENT_PRIORITY_ORDER) - idx) * 0.1
            return base_score

        sorted_intents = sorted(intents, key=_score, reverse=True)
        return sorted_intents[0].classified_intent_id


default_grouping_engine = IntentGroupingEngine()
