from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from app.domain.journey.integration.strategies.base import CompositionStrategy

if TYPE_CHECKING:
    from app.domain.journey.integration.models import JourneyIntelligenceContext

class ExecutiveStrategy(CompositionStrategy):
    """Strategy that summarizes high-level data for executives."""
    
    def apply(self, context: JourneyIntelligenceContext) -> JourneyIntelligenceContext:
        # Filter for executive view blocks or summarize existing blocks
        return dataclasses.replace(
            context,
            blocks=[b for b in context.blocks if b.block_type in ("summary", "executive")]
        )
