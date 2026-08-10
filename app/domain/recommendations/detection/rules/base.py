from abc import ABC, abstractmethod
from typing import List, Any

class AbstractRecommendationDetectionRule(ABC):
    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass
        
    @property
    @abstractmethod
    def rule_name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def rule_version(self) -> str:
        pass
        
    @property
    @abstractmethod
    def supported_recommendation_types(self) -> List[str]:
        pass

    @abstractmethod
    def evaluate(self, context: Any) -> List[Any]:
        """
        Evaluate the context and return a list of RecommendationCandidate objects.
        Context: RecommendationDetectionContext
        Returns: list[RecommendationCandidate]
        """
        pass
