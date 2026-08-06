"""
HunterOS Engage V1 - Abstract Intent View Base
Projections for multi-perspective intent reporting.
"""

from __future__ import annotations

import abc
from typing import Any, Dict

from app.domain.intents.models import IntentDetectionResult


class AbstractIntentView(abc.ABC):
    """Abstract base for intent view projections."""

    @property
    @abc.abstractmethod
    def view_name(self) -> str:
        """Identifier for the view projection."""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Description of the perspective and target audience."""
        pass

    @abc.abstractmethod
    def render(self, result: IntentDetectionResult) -> Dict[str, Any]:
        """Project the aggregate result into the view format."""
        pass
