from typing import Any, Dict, Optional
from .pipeline import RecommendationIntegrationPipeline
from .strategies.base import RecommendationCompositionStrategy

class RecommendationIntelligenceGateway:
    """
    Facade wrapping the integration pipeline, cache, and repository.
    Strictly assembles and serves data without calling detection or prioritization engines.
    """
    def __init__(self, pipeline: RecommendationIntegrationPipeline, cache: Any = None, repository: Any = None):
        self.pipeline = pipeline
        self.cache = cache
        self.repository = repository

    def get_recommendation(
        self,
        recommendation_id: str,
        strategy: Optional[RecommendationCompositionStrategy] = None
    ) -> Dict[str, Any]:
        """
        Retrieves a recommendation by ID, applying the requested composition strategy.
        Uses cache if available, and relies on the pipeline to assemble pre-computed artifacts.
        """
        if self.cache:
            cached_result = self.cache.get(recommendation_id)
            if cached_result:
                return cached_result

        # Retrieve artifact references from repository (simulated)
        if self.repository:
            refs = self.repository.get_artifact_refs(recommendation_id)
        else:
            refs = {
                "detection_ref": f"det_{recommendation_id}",
                "prioritization_ref": f"pri_{recommendation_id}",
                "explanation_ref": f"exp_{recommendation_id}"
            }

        # Execute pipeline
        result = self.pipeline.execute(
            detection_ref=refs.get("detection_ref"),
            prioritization_ref=refs.get("prioritization_ref"),
            explanation_ref=refs.get("explanation_ref"),
            strategy=strategy
        )

        if self.cache:
            self.cache.set(recommendation_id, result)

        return result
