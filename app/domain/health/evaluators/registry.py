from typing import List

from app.domain.health.evaluators.base import BaseHealthEvaluator


class HealthRegistry:
    """
    Registry for Health Evaluators.
    Maintains a list of all active health domains in HunterOS.
    """
    def __init__(self):
        self._evaluators: List[BaseHealthEvaluator] = []

    def register(self, evaluator: BaseHealthEvaluator) -> None:
        self._evaluators.append(evaluator)

    def get_all_evaluators(self) -> List[BaseHealthEvaluator]:
        return self._evaluators


health_registry = HealthRegistry()
