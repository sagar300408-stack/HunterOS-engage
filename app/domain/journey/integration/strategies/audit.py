from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from app.domain.journey.integration.strategies.base import CompositionStrategy

if TYPE_CHECKING:
    from app.domain.journey.integration.models import JourneyIntelligenceContext

class AuditStrategy(CompositionStrategy):
    """Strategy that filters or summarizes context blocks for an audit view."""
    
    def apply(self, context: JourneyIntelligenceContext) -> JourneyIntelligenceContext:
        return dataclasses.replace(
            context,
            blocks=[b for b in context.blocks if b.block_type in ("audit", "history", "provenance")]
        )
