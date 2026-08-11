from typing import Any, Dict, Optional
from .base import RecommendationCompositionStrategy

class CustomStrategy(RecommendationCompositionStrategy):
    def assemble(
        self,
        detection_artifact: Optional[Dict[str, Any]] = None,
        prioritization_artifact: Optional[Dict[str, Any]] = None,
        explanation_artifact: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "type": "custom",
            "detection": detection_artifact or {},
            "prioritization": prioritization_artifact or {},
            "explanation": explanation_artifact or {}
        }
