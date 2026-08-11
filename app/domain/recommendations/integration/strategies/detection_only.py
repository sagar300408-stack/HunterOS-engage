from typing import Any, Dict, Optional
from .base import RecommendationCompositionStrategy

class DetectionOnlyStrategy(RecommendationCompositionStrategy):
    def assemble(
        self,
        detection_artifact: Optional[Dict[str, Any]] = None,
        prioritization_artifact: Optional[Dict[str, Any]] = None,
        explanation_artifact: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "type": "detection_only",
            "data": detection_artifact or {}
        }
