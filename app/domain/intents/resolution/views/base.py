"""
HunterOS Engage V1 - Resolution Views Base
Abstract base class for multi-perspective projections of multi-intent resolution models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.domain.intents.resolution.models import MultiIntentResolutionResult


class BaseResolutionView(ABC):
    """
    Abstract base for role-tailored read-only projections of resolution results.
    Never modifies state or recommends actions.
    """

    @abstractmethod
    def render(self, result: MultiIntentResolutionResult) -> Dict[str, Any]:
        """Project result into a structured role-tailored view dictionary."""
        pass
