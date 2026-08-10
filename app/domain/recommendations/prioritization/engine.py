from typing import List, Any
from .stages.load_candidates import LoadCandidatesStage
from .stages.normalize_candidates import NormalizeCandidatesStage
from .stages.calculate_factors import CalculateFactorsStage
from .stages.calculate_priority import CalculatePriorityStage
from .stages.validate_prioritization import ValidatePrioritizationStage
from .stages.resolve_ties import ResolveTiesStage
from .stages.generate_result import GenerateResultStage

class RecommendationPrioritizationEngine:
    def __init__(self):
        self.stages = [
            LoadCandidatesStage(),
            NormalizeCandidatesStage(),
            CalculateFactorsStage(),
            CalculatePriorityStage(),
            ValidatePrioritizationStage(),
            ResolveTiesStage(),
            GenerateResultStage()
        ]

    def execute(self, candidates: List[Any], context: Any) -> Any:
        state = {"candidates": candidates, "context": context}
        for stage in self.stages:
            state = stage.process(state)
        return state.get("result")
