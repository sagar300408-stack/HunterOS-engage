"""
HunterOS Engage V1 - Real Estate Classification Rule Pack
Specialized real estate intent classification rules.
"""

from __future__ import annotations

from typing import List, Optional

from app.domain.intents.classification.canonical.models import CanonicalIntent
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)
from app.domain.intents.classification.rules.base import (
    AbstractClassificationRule,
    AbstractClassificationRulePack,
    ClassificationCandidate,
)


class PropertyInquiryClassificationRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="PropertyInquiryClassificationRule",
            rule_version=rule_version,
            description="Classifies real estate unit, BHK, flat, or villa inquiries into Real Estate domain.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if "property_inquiry" in canonical.canonical_name.lower() or any(
            k in raw for k in ["bhk", "flat", "villa", "apartment", "square feet", "sqft", "sq.ft", "property"]
        ):
            return ClassificationCandidate(
                category=IntentCategory.INFORMATION,
                domain=BusinessDomain.REAL_ESTATE,
                process="LEAD_CAPTURE",
                taxonomy_node_id="information.property_inquiry",
                confidence_boost=0.08,
                aliases=["PROPERTY_INQUIRY", "REAL_ESTATE_INQUIRY"],
            )
        return None


class SiteVisitRealEstateRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="SiteVisitRealEstateRule",
            rule_version=rule_version,
            description="Classifies property site visits / model apartment tours into Real Estate domain.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if ("visit" in raw or "tour" in raw) and any(k in raw for k in ["site", "sample flat", "property", "project", "model apartment"]):
            return ClassificationCandidate(
                category=IntentCategory.OPERATIONAL,
                domain=BusinessDomain.REAL_ESTATE,
                process="APPOINTMENT_SCHEDULING",
                taxonomy_node_id="operational.site_visit",
                confidence_boost=0.08,
                aliases=["SCHEDULE_SITE_VISIT", "PROPERTY_TOUR"],
            )
        return None


class RealEstateClassificationRulePack(AbstractClassificationRulePack):
    """
    Real Estate domain-specific rule pack.
    """

    def __init__(self, version: str = "1.0.0"):
        super().__init__(
            pack_name="RealEstateClassificationRulePack",
            version=version,
            description="Real Estate vertical intent classification rules.",
        )
        self._rules: List[AbstractClassificationRule] = [
            PropertyInquiryClassificationRule(rule_version=version),
            SiteVisitRealEstateRule(rule_version=version),
        ]

    def get_rules(self) -> List[AbstractClassificationRule]:
        return list(self._rules)
