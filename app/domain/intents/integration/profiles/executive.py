"""
HunterOS Engage V1 - Executive Composition Profile
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext
from app.domain.intents.integration.profiles.full import FullProfile


class ExecutiveProfile(FullProfile):
    """Composition profile synthesizing executive-level strategic intelligence."""

    def __init__(self) -> None:
        super().__init__()
        self.profile_name = "ExecutiveProfile"
        self.profile_type = CompositionProfileType.EXECUTIVE
        self.description = "Executive intelligence perspective highlighting strategic focus and friction."

    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        context.executive_view = self._build_executive_view(context)
