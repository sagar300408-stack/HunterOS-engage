from typing import List

from app.domain.recommendation.generators.base import BaseRecommendationGenerator


class RecommendationRegistry:
    """
    Registry for Recommendation Generators.
    """
    def __init__(self):
        self._generators: List[BaseRecommendationGenerator] = []

    def register(self, generator: BaseRecommendationGenerator) -> None:
        self._generators.append(generator)

    def get_all_generators(self) -> List[BaseRecommendationGenerator]:
        return self._generators


recommendation_registry = RecommendationRegistry()
