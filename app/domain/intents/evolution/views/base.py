"""
HunterOS Engage V1 - Evolution View Base
Abstract base class for perspective-specific projections of IntentEvolutionResult.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.domain.intents.evolution.models import IntentEvolutionResult


class AbstractEvolutionView(ABC):
    """
    Abstract view projection converting an IntentEvolutionResult into a role-tailored representation.
    """

    def __init__(self, view_name: str):
        self.view_name: str = view_name

    @abstractmethod
    def project(self, result: IntentEvolutionResult) -> Dict[str, Any]:
        """Project the evolution result into a role-specific dictionary payload."""
        pass
