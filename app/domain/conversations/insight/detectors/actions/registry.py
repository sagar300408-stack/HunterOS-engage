"""
HunterOS Engage V1 - Action Item Detector Registry
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Registry for managing and executing pluggable action item detection rules.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.detectors.actions.base import AbstractActionItemDetector
from app.domain.conversations.insight.models import ActionItemInsight

logger = logging.getLogger(__name__)


class ActionItemDetectorRegistry:
    """Registry coordinating all active action item detectors."""

    def __init__(self) -> None:
        self._detectors: Dict[str, AbstractActionItemDetector] = {}

    def register(self, detector: AbstractActionItemDetector) -> None:
        """Registers an action item detector."""
        self._detectors[detector.detector_name] = detector
        logger.debug("Registered ActionItemDetector: %s", detector.detector_name)

    def unregister(self, detector_name: str) -> Optional[AbstractActionItemDetector]:
        """Unregisters an action item detector."""
        return self._detectors.pop(detector_name, None)

    def get(self, detector_name: str) -> Optional[AbstractActionItemDetector]:
        """Retrieves an action item detector by name."""
        return self._detectors.get(detector_name)

    def list_detectors(self) -> List[str]:
        """Returns names of all registered detectors."""
        return list(self._detectors.keys())

    def detect_all(self, context: ConversationInsightContext) -> List[ActionItemInsight]:
        """Executes all registered detectors and aggregates candidate action items."""
        actions: List[ActionItemInsight] = []
        for name, detector in self._detectors.items():
            try:
                detected = detector.detect(context)
                actions.extend(detected)
                logger.debug("Detector %s identified %d action items", name, len(detected))
            except Exception as e:
                logger.error("Action detector %s failed: %s", name, str(e), exc_info=True)
                context.add_warning(f"Action detector {name} failed: {str(e)}")
        return actions


default_action_item_detector_registry = ActionItemDetectorRegistry()
