from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from app.domain.journey.integration.strategies.base import CompositionStrategy

if TYPE_CHECKING:
    from app.domain.journey.integration.models import JourneyIntelligenceContext

class FullStrategy(CompositionStrategy):
    """Strategy that includes all context blocks."""
    
    def apply(self, context: JourneyIntelligenceContext) -> JourneyIntelligenceContext:
        # Full strategy just returns the context as is
        return context
