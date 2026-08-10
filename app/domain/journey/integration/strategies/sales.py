from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from app.domain.journey.integration.strategies.base import CompositionStrategy

if TYPE_CHECKING:
    from app.domain.journey.integration.models import JourneyIntelligenceContext

class SalesStrategy(CompositionStrategy):
    """Strategy that filters or summarizes context blocks for a sales view."""
    
    def apply(self, context: JourneyIntelligenceContext) -> JourneyIntelligenceContext:
        return dataclasses.replace(
            context,
            blocks=[b for b in context.blocks if b.block_type in ("sales", "journey", "summary")]
        )
