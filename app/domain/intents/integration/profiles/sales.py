"""
HunterOS Engage V1 - Sales Composition Profile
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext
from app.domain.intents.integration.profiles.full import FullProfile


class SalesProfile(FullProfile):
    """Composition profile synthesizing deal velocity and commercial signals."""

    def __init__(self) -> None:
        super().__init__()
        self.profile_name = "SalesProfile"
        self.profile_type = CompositionProfileType.SALES
        self.description = "Sales intelligence perspective highlighting buying signals, deal blockers, and commercial friction."

    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        context.sales_view = self._build_sales_view(context)
