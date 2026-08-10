from __future__ import annotations
import abc
from dataclasses import dataclass

@dataclass(frozen=True)
class AbstractRecommendationRule(abc.ABC):
    rule_id: str
    rule_name: str
    version: str
    supported_recommendation_types: frozenset[str]

    @abc.abstractmethod
    def evaluate(self, *args, **kwargs) -> bool:
        """Evaluate the rule."""
        pass
