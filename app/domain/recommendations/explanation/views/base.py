from abc import ABC, abstractmethod
from ..models import RecommendationExplanation

class BaseView(ABC):
    @abstractmethod
    def render(self, explanation: RecommendationExplanation) -> str:
        pass
