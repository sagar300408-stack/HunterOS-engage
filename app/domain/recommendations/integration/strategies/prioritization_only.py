from typing import Any, Dict, Optional
from .base import RecommendationCompositionStrategy

class PrioritizationOnlyStrategy(RecommendationCompositionStrategy):
    def assemble(
        self,
        detection_artifact: Optional[Dict[str, Any]] = None,
        prioritization_artifact: Optional[Dict[str, Any]] = None,
        explanation_artifact: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "type": "prioritization_only",
            "data": prioritization_artifact or {}
        }
