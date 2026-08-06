"""
HunterOS Engage V1 - Intent Recognizer
First phase of intent intelligence: Identifies candidate customer intents via pluggable providers.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.domain.intents.context import IntentDetectionContext
from app.domain.intents.models import DetectedIntent, RuleExecutionReport
from app.domain.intents.providers.base import IntentDetectorProvider
from app.domain.intents.providers.rule_based import RuleBasedIntentDetectorProvider


class IntentRecognizer:
    """
    Dedicated component responsible for recognizing candidate intents from conversation artifacts.
    Decoupled from validation and resolution to support future hybrid ML/LLM providers.
    """

    def __init__(self, provider: Optional[IntentDetectorProvider] = None):
        self._provider = provider or RuleBasedIntentDetectorProvider()

    @property
    def provider(self) -> IntentDetectorProvider:
        return self._provider

    def recognize(
        self, context: IntentDetectionContext
    ) -> Tuple[List[DetectedIntent], RuleExecutionReport]:
        """
        Runs the configured provider to detect candidate intents.
        Returns:
            Tuple of (raw candidate intents, rule execution report).
        """
        return self._provider.detect_candidates(context)
