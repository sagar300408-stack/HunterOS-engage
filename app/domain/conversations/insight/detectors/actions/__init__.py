"""
HunterOS Engage V1 - Action Item Detectors Package
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from app.domain.conversations.insight.detectors.actions.base import AbstractActionItemDetector
from app.domain.conversations.insight.detectors.actions.registry import (
    ActionItemDetectorRegistry,
    default_action_item_detector_registry,
)
from app.domain.conversations.insight.detectors.actions.standard import (
    CustomActionItemDetector,
    CustomerActionItemDetector,
    InternalTeamActionItemDetector,
    PendingResponseActionItemDetector,
    RequestedDocumentActionItemDetector,
    ScheduledActivityActionItemDetector,
    SharedActionItemDetector,
    register_standard_action_item_detectors,
)

__all__ = [
    "AbstractActionItemDetector",
    "ActionItemDetectorRegistry",
    "default_action_item_detector_registry",
    "CustomerActionItemDetector",
    "InternalTeamActionItemDetector",
    "SharedActionItemDetector",
    "PendingResponseActionItemDetector",
    "RequestedDocumentActionItemDetector",
    "ScheduledActivityActionItemDetector",
    "CustomActionItemDetector",
    "register_standard_action_item_detectors",
]
