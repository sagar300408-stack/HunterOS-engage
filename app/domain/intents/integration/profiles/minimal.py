"""
HunterOS Engage V1 - Minimal Composition Profile (Detection Only)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext
from app.domain.intents.integration.profiles.base import CompositionProfile


class MinimalProfile(CompositionProfile):
    """Minimal composition profile providing only raw Intent Detection artifacts."""

    def __init__(self) -> None:
        super().__init__(
            profile_name="MinimalProfile",
            profile_type=CompositionProfileType.MINIMAL,
            required_modules=["DETECTION"],
            description="Minimal intent context with raw detected intents and taxonomy categories.",
        )

    @property
    def include_classification(self) -> bool:
        return False

    @property
    def include_evolution(self) -> bool:
        return False

    @property
    def include_resolution(self) -> bool:
        return False

    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        # Clear non-detection fields
        context.classification_result = None
        context.evolution_result = None
        context.resolution_result = None
