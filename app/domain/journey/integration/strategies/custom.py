from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Callable, List, Any

from app.domain.journey.integration.strategies.base import CompositionStrategy

if TYPE_CHECKING:
    from app.domain.journey.integration.models import JourneyIntelligenceContext

class CustomStrategy(CompositionStrategy):
    """Strategy that applies a custom filter function to context blocks."""
    
    def __init__(self, filter_func: Callable[[Any], bool]):
        self.filter_func = filter_func

    def apply(self, context: JourneyIntelligenceContext) -> JourneyIntelligenceContext:
        return dataclasses.replace(
            context,
            blocks=[b for b in context.blocks if self.filter_func(b)]
        )
