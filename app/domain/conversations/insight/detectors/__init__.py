"""
HunterOS Engage V1 - Insight Detectors Package
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from app.domain.conversations.insight.detectors.actions import (
    ActionItemDetectorRegistry,
    default_action_item_detector_registry,
)
from app.domain.conversations.insight.detectors.opportunities import (
    OpportunityDetectorRegistry,
    default_opportunity_detector_registry,
)
from app.domain.conversations.insight.detectors.risks import (
    RiskDetectorRegistry,
    default_risk_detector_registry,
)

__all__ = [
    "RiskDetectorRegistry",
    "default_risk_detector_registry",
    "OpportunityDetectorRegistry",
    "default_opportunity_detector_registry",
    "ActionItemDetectorRegistry",
    "default_action_item_detector_registry",
]
