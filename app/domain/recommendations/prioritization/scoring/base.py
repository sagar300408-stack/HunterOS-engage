from abc import ABC, abstractmethod
from typing import Any, Dict

class PriorityFactor:
    def __init__(self, score: float, weight: float, reason_code: str, details: Dict[str, Any] = None):
        self.score = score
        self.weight = weight
        self.reason_code = reason_code
        self.details = details or {}

class AbstractPriorityFactor(ABC):
    @abstractmethod
    def factor_type(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, candidate: Any, context: Any) -> PriorityFactor:
        pass

    @abstractmethod
    def weight(self) -> float:
        pass

    @abstractmethod
    def reason_code(self) -> str:
        pass
