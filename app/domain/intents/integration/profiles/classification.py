"""
HunterOS Engage V1 - Classification Composition Profile
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext
from app.domain.intents.integration.profiles.base import CompositionProfile


class ClassificationProfile(CompositionProfile):
    """Composition profile providing classified business processes and domain taxonomy."""

    def __init__(self) -> None:
        super().__init__(
            profile_name="ClassificationProfile",
            profile_type=CompositionProfileType.CLASSIFICATION,
            required_modules=["CLASSIFICATION"],
            description="Intent context focused on enterprise taxonomy paths and business processes.",
        )

    @property
    def include_evolution(self) -> bool:
        return False

    @property
    def include_resolution(self) -> bool:
        return False

    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        context.evolution_result = None
        context.resolution_result = None
