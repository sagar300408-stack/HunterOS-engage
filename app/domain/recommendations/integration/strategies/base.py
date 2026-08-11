from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class RecommendationCompositionStrategy(ABC):
    """
    Abstract base class defining a deterministic assembly contract for recommendation integration.
    """
    @abstractmethod
    def assemble(
        self,
        detection_artifact: Optional[Dict[str, Any]] = None,
        prioritization_artifact: Optional[Dict[str, Any]] = None,
        explanation_artifact: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass
