from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.journey.integration.models import JourneyIntelligenceContext

class CompositionStrategy(ABC):
    """Base abstract class for composition strategies."""
    
    @abstractmethod
    def apply(self, context: JourneyIntelligenceContext) -> JourneyIntelligenceContext:
        """
        Apply the composition strategy to a context, returning a new immutable context.
        """
        pass
