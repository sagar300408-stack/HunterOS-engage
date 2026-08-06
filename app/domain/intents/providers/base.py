"""
HunterOS Engage V1 - Intent Detector Provider Interface
Abstract base for pluggable detector strategies (Rule-Based, ML, LLM, Hybrid).
"""

from __future__ import annotations

import abc
from typing import List, Tuple

from app.domain.intents.context import IntentDetectionContext
from app.domain.intents.models import DetectedIntent, RuleExecutionReport


class IntentDetectorProvider(abc.ABC):
    """
    Abstract interface for intent detection providers.
    Enables future hybrid detection (LLM, ML, Rules) without touching core pipeline architecture.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'RuleBased', 'LLM', 'Hybrid')."""
        pass

    @property
    @abc.abstractmethod
    def provider_version(self) -> str:
        """Version string of the provider implementation."""
        pass

    @abc.abstractmethod
    def detect_candidates(
        self, context: IntentDetectionContext
    ) -> Tuple[List[DetectedIntent], RuleExecutionReport]:
        """
        Execute candidate detection over the given context.
        Returns:
            Tuple of (detected candidate intents, rule execution report).
        """
        pass
