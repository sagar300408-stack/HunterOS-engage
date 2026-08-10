from .base import AbstractPriorityFactor, PriorityFactor
from .registry import PriorityFactorRegistry
from typing import Any

@PriorityFactorRegistry.register
class ImpactFactor(AbstractPriorityFactor):
    def factor_type(self) -> str:
        return "impact"
    
    def evaluate(self, candidate: Any, context: Any) -> PriorityFactor:
        # Deterministic dummy scoring
        score = getattr(candidate, "impact_score", 0.5)
        return PriorityFactor(score=score, weight=self.weight(), reason_code=self.reason_code(), details={})
        
    def weight(self) -> float:
        return 1.0
        
    def reason_code(self) -> str:
        return "IMPACT_EVALUATED"
