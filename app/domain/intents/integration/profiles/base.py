"""
HunterOS Engage V1 - Composition Profile Base Class
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Abstract base class for all Intent Intelligence Composition Profiles.
Profiles declare WHAT should be assembled, while assemblers execute HOW.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.intents.integration.models import (
    CompositionProfileType,
    ExecutiveIntentContext,
    SalesIntentContext,
    OperationsIntentContext,
    AuditIntentContext,
    CustomIntentContext,
    IntentIntelligenceContext,
)


class CompositionProfile(ABC):
    """
    Abstract Base Class for declarative composition profiles.
    Encapsulates inclusion policies, role perspective transformations, and assembly filtering.
    """

    def __init__(
        self,
        profile_name: str = "CUSTOM",
        profile_type: CompositionProfileType = CompositionProfileType.CUSTOM,
        required_modules: Optional[List[str]] = None,
        description: str = "",
    ) -> None:
        self._profile_name = profile_name
        self._profile_type = profile_type
        self.required_modules = required_modules or []
        self.description = description

    @property
    def profile_name(self) -> str:
        return getattr(self, "_profile_name", "CUSTOM")

    @profile_name.setter
    def profile_name(self, value: str) -> None:
        self._profile_name = value

    @property
    def profile_type(self) -> CompositionProfileType:
        return getattr(self, "_profile_type", CompositionProfileType.CUSTOM)

    @profile_type.setter
    def profile_type(self, value: CompositionProfileType) -> None:
        self._profile_type = value

    @property
    def include_detection(self) -> bool:
        return True

    @property
    def include_classification(self) -> bool:
        return True

    @property
    def include_evolution(self) -> bool:
        return True

    @property
    def include_resolution(self) -> bool:
        return True

    @property
    def include_conversation_context(self) -> bool:
        return True

    @abstractmethod
    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        """Apply profile-specific transformations, projections, and filtering to the context."""
        pass
