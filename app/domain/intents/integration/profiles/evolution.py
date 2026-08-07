"""
HunterOS Engage V1 - Evolution Composition Profile
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext
from app.domain.intents.integration.profiles.base import CompositionProfile


class EvolutionProfile(CompositionProfile):
    """Composition profile providing historical timelines and lifecycle state transitions."""

    def __init__(self) -> None:
        super().__init__(
            profile_name="EvolutionProfile",
            profile_type=CompositionProfileType.EVOLUTION,
            required_modules=["EVOLUTION"],
            description="Intent context focused on intent history, multi-turn trajectories, and velocity.",
        )

    @property
    def include_resolution(self) -> bool:
        return False

    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        context.resolution_result = None
