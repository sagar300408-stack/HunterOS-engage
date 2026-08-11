import logging
from typing import Any
from app.events.model.intelligence_events import RecommendationCreatedEvent
from app.domain.operations.intelligence.engine import ActionIntelligenceEngine
from app.domain.recommendations.engine import RecommendationIntelligenceEngine

logger = logging.getLogger(__name__)

class RecommendationEventHandler:
    """
    Subscribes to Phase 2 Recommendation events and triggers Phase 3.2 Action Intelligence.
    Ensures that events from the outside world enter the Intelligence boundary cleanly.
    """

    def __init__(
        self,
        recommendation_engine: RecommendationIntelligenceEngine,
        action_intel_engine: ActionIntelligenceEngine,
    ):
        self.recommendation_engine = recommendation_engine
        self.action_intel_engine = action_intel_engine

    async def handle_recommendation_created(self, event: RecommendationCreatedEvent) -> None:
        """
        Handles the creation of a recommendation by fetching its full context
        and evaluating it through the Action Intelligence Engine.
        """
        try:
            # Note: We must ensure this fetch doesn't mutate or bypass security boundaries.
            # Assuming the recommendation_engine provides a safe read for the given workspace_id.
            recommendation = self.recommendation_engine.get(event.recommendation_id)
            
            # Security & Isolation: Enforce workspace matching
            if recommendation.workspace_id != event.workspace_id:
                logger.error(f"Workspace mismatch for recommendation {event.recommendation_id}")
                return

            result = await self.action_intel_engine.evaluate_recommendation(recommendation)

            logger.info(f"Action Intelligence Result for {event.recommendation_id}: {result.outcome.value} - {result.explanation}")

        except Exception as e:
            logger.exception(f"Failed to process RecommendationCreatedEvent for {event.recommendation_id}: {str(e)}")
