"""
HunterOS Engage V1 - Operations Composition Profile
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext
from app.domain.intents.integration.profiles.full import FullProfile


class OperationsProfile(FullProfile):
    """Composition profile synthesizing fulfillment, service, and document dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self.profile_name = "OperationsProfile"
        self.profile_type = CompositionProfileType.OPERATIONS
        self.description = "Operations intelligence perspective highlighting support, document requests, and blockers."

    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        context.operations_view = self._build_operations_view(context)
