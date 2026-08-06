"""
HunterOS Engage V1 - Risk Detector Registry
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Registry for managing and executing pluggable risk detection algorithms.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.domain.conversations.insight.context import ConversationInsightContext
from app.domain.conversations.insight.detectors.risks.base import AbstractRiskDetector
from app.domain.conversations.insight.models import RiskInsight

logger = logging.getLogger(__name__)


class RiskDetectorRegistry:
    """Registry coordinating all active risk detectors."""

    def __init__(self) -> None:
        self._detectors: Dict[str, AbstractRiskDetector] = {}

    def register(self, detector: AbstractRiskDetector) -> None:
        """Registers a risk detector."""
        self._detectors[detector.detector_name] = detector
        logger.debug("Registered RiskDetector: %s", detector.detector_name)

    def unregister(self, detector_name: str) -> Optional[AbstractRiskDetector]:
        """Unregisters a risk detector."""
        return self._detectors.pop(detector_name, None)

    def get(self, detector_name: str) -> Optional[AbstractRiskDetector]:
        """Retrieves a detector by name."""
        return self._detectors.get(detector_name)

    def list_detectors(self) -> List[str]:
        """Returns names of all registered detectors."""
        return list(self._detectors.keys())

    def detect_all(self, context: ConversationInsightContext) -> List[RiskInsight]:
        """Executes all registered detectors and aggregates candidate risks."""
        risks: List[RiskInsight] = []
        for name, detector in self._detectors.items():
            try:
                detected = detector.detect(context)
                risks.extend(detected)
                logger.debug("Detector %s identified %d risks", name, len(detected))
            except Exception as e:
                logger.error("Risk detector %s failed: %s", name, str(e), exc_info=True)
                context.add_warning(f"Risk detector {name} failed: {str(e)}")
        return risks


default_risk_detector_registry = RiskDetectorRegistry()
