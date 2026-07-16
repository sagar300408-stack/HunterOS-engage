from typing import List

from app.domain.insight.generators.base import BaseInsightGenerator


class InsightRegistry:
    """
    Registry for Insight Generators.
    """
    def __init__(self):
        self._generators: List[BaseInsightGenerator] = []

    def register(self, generator: BaseInsightGenerator) -> None:
        self._generators.append(generator)

    def get_all_generators(self) -> List[BaseInsightGenerator]:
        return self._generators


insight_registry = InsightRegistry()
