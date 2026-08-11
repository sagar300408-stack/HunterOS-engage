from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ExplanationSection(BaseModel):
    title: str
    content: str
    evidence_refs: List[str] = []

class AbstractRecommendationExplanationRule(ABC):
    @abstractmethod
    def explain(self, context: Dict[str, Any]) -> Optional[ExplanationSection]:
        """
        Explain a specific factor based on the provided context.
        Must be deterministic and not recalculate scores.
        """
        pass
