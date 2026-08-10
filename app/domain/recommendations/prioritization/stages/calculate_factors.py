from . import PipelineStage
from typing import Dict, Any
from ..scoring.registry import PriorityFactorRegistry

class CalculateFactorsStage(PipelineStage):
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        factors = PriorityFactorRegistry.get_all_instances()
        for candidate in state["candidates"]:
            candidate.factors = {}
            for factor in factors:
                candidate.factors[factor.factor_type()] = factor.evaluate(candidate, state["context"])
        return state
