"""
HunterOS Engage V1 - Opportunity Detectors Package
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from app.domain.conversations.insight.detectors.opportunities.base import AbstractOpportunityDetector
from app.domain.conversations.insight.detectors.opportunities.registry import (
    OpportunityDetectorRegistry,
    default_opportunity_detector_registry,
)
from app.domain.conversations.insight.detectors.opportunities.standard import (
    AdditionalRequirementOpportunityDetector,
    CrossSellOpportunityDetector,
    CustomOpportunityDetector,
    DocumentSharingOpportunityDetector,
    FollowUpOpportunityDetector,
    MeetingOpportunityDetector,
    QualificationOpportunityDetector,
    UpsellOpportunityDetector,
    register_standard_opportunity_detectors,
)

__all__ = [
    "AbstractOpportunityDetector",
    "OpportunityDetectorRegistry",
    "default_opportunity_detector_registry",
    "UpsellOpportunityDetector",
    "CrossSellOpportunityDetector",
    "AdditionalRequirementOpportunityDetector",
    "FollowUpOpportunityDetector",
    "DocumentSharingOpportunityDetector",
    "MeetingOpportunityDetector",
    "QualificationOpportunityDetector",
    "CustomOpportunityDetector",
    "register_standard_opportunity_detectors",
]
