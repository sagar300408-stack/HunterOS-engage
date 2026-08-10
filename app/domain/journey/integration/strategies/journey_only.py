from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from app.domain.journey.integration.strategies.base import CompositionStrategy

if TYPE_CHECKING:
    from app.domain.journey.integration.models import JourneyIntelligenceContext

class JourneyOnlyStrategy(CompositionStrategy):
    """Strategy that filters context blocks to only include journey-specific data."""
    
    def apply(self, context: JourneyIntelligenceContext) -> JourneyIntelligenceContext:
        # Reconstruct the context keeping only journey blocks, omitting maturity, analytics, history
        return dataclasses.replace(
            context,
            blocks=[b for b in context.blocks if b.block_type == "journey"]
        )
