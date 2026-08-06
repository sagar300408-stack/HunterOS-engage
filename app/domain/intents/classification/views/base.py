"""
HunterOS Engage V1 - Classification View Base Class
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.domain.intents.classification.models import IntentClassificationResult


class AbstractClassificationView(ABC):
    """Base class for multi-perspective intent classification projection views."""

    def __init__(self, view_name: str, description: str = ""):
        self.view_name = view_name
        self.description = description

    @abstractmethod
    def generate(self, result: IntentClassificationResult) -> Dict[str, Any]:
        """Generate projection view from IntentClassificationResult."""
        pass
