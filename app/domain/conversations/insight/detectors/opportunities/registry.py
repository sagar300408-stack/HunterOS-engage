"""
HunterOS Engage V1 - Opportunity Detector Registry
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Registry for managing and executing pluggable opportunity detection algorithms.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.detectors.opportunities.base import AbstractOpportunityDetector
from app.domain.conversations.insight.models import OpportunityInsight

logger = logging.getLogger(__name__)


class OpportunityDetectorRegistry:
    """Registry coordinating all active opportunity detectors."""

    def __init__(self) -> None:
        self._detectors: Dict[str, AbstractOpportunityDetector] = {}

    def register(self, detector: AbstractOpportunityDetector) -> None:
        """Registers an opportunity detector."""
        self._detectors[detector.detector_name] = detector
        logger.debug("Registered OpportunityDetector: %s", detector.detector_name)

    def unregister(self, detector_name: str) -> Optional[AbstractOpportunityDetector]:
        """Unregisters an opportunity detector."""
        return self._detectors.pop(detector_name, None)

    def get(self, detector_name: str) -> Optional[AbstractOpportunityDetector]:
        """Retrieves a detector by name."""
        return self._detectors.get(detector_name)

    def list_detectors(self) -> List[str]:
        """Returns names of all registered detectors."""
        return list(self._detectors.keys())

    def detect_all(self, context: ConversationInsightContext) -> List[OpportunityInsight]:
        """Executes all registered detectors and aggregates candidate opportunities."""
        opportunities: List[OpportunityInsight] = []
        for name, detector in self._detectors.items():
            try:
                detected = detector.detect(context)
                opportunities.extend(detected)
                logger.debug("Detector %s identified %d opportunities", name, len(detected))
            except Exception as e:
                logger.error("Opportunity detector %s failed: %s", name, str(e), exc_info=True)
                context.add_warning(f"Opportunity detector {name} failed: {str(e)}")
        return opportunities


default_opportunity_detector_registry = OpportunityDetectorRegistry()
