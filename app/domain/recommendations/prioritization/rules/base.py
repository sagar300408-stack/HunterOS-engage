from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

class FactorAdjustment(BaseModel):
    rule_name: str
    factor_name: str
    adjustment_value: float
    reason: str

class AbstractPrioritizationRule(ABC):
    @property
    @abstractmethod
    def rule_name(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        """
        Evaluate the rule and return a list of factor adjustments.
        Must NOT create recommendations.
        """
        pass
