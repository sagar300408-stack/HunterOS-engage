import os

base_dir = r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\recommendations\prioritization"

os.makedirs(os.path.join(base_dir, "scoring"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "stages"), exist_ok=True)

# 1. scoring/base.py
with open(os.path.join(base_dir, "scoring", "base.py"), "w", encoding="utf-8") as f:
    f.write("""from abc import ABC, abstractmethod
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
""")

# 2. scoring/registry.py
with open(os.path.join(base_dir, "scoring", "registry.py"), "w", encoding="utf-8") as f:
    f.write("""from typing import Dict, Type
from .base import AbstractPriorityFactor

class PriorityFactorRegistry:
    _factors: Dict[str, Type[AbstractPriorityFactor]] = {}

    @classmethod
    def register(cls, factor_class: Type[AbstractPriorityFactor]):
        instance = factor_class()
        cls._factors[instance.factor_type()] = factor_class
        return factor_class

    @classmethod
    def get_all_instances(cls):
        return [factor_class() for factor_class in cls._factors.values()]
""")

# 3. scoring factors
factors = ["urgency", "impact", "evidence", "freshness", "blocking", "business_value", "confidence"]
for factor in factors:
    class_name = "".join(word.capitalize() for word in factor.split("_")) + "Factor"
    with open(os.path.join(base_dir, "scoring", f"{factor}.py"), "w", encoding="utf-8") as f:
        f.write(f"""from .base import AbstractPriorityFactor, PriorityFactor
from .registry import PriorityFactorRegistry
from typing import Any

@PriorityFactorRegistry.register
class {class_name}(AbstractPriorityFactor):
    def factor_type(self) -> str:
        return "{factor}"
    
    def evaluate(self, candidate: Any, context: Any) -> PriorityFactor:
        # Deterministic dummy scoring
        score = getattr(candidate, "{factor}_score", 0.5)
        return PriorityFactor(score=score, weight=self.weight(), reason_code=self.reason_code(), details={{}})
        
    def weight(self) -> float:
        return 1.0
        
    def reason_code(self) -> str:
        return "{factor.upper()}_EVALUATED"
""")

# scoring/__init__.py
with open(os.path.join(base_dir, "scoring", "__init__.py"), "w", encoding="utf-8") as f:
    imports = "\\n".join([f"from .{factor} import *" for factor in factors])
    f.write(f"""from .base import AbstractPriorityFactor, PriorityFactor
from .registry import PriorityFactorRegistry
{imports}
""")

# 4. engine.py
with open(os.path.join(base_dir, "engine.py"), "w", encoding="utf-8") as f:
    f.write("""from typing import List, Any
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
""")

# stages base
with open(os.path.join(base_dir, "stages", "__init__.py"), "w", encoding="utf-8") as f:
    f.write("""from abc import ABC, abstractmethod
from typing import Dict, Any

class PipelineStage(ABC):
    @abstractmethod
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass
""")

# stages implementations
stages_code = {
    "load_candidates.py": """from . import PipelineStage
from typing import Dict, Any

class LoadCandidatesStage(PipelineStage):
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Validate/load candidates
        return state
""",
    "normalize_candidates.py": """from . import PipelineStage
from typing import Dict, Any

class NormalizeCandidatesStage(PipelineStage):
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Normalize
        return state
""",
    "calculate_factors.py": """from . import PipelineStage
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
""",
    "calculate_priority.py": """from . import PipelineStage
from typing import Dict, Any

class CalculatePriorityStage(PipelineStage):
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        for candidate in state["candidates"]:
            total_score = 0.0
            total_weight = 0.0
            for factor_res in getattr(candidate, "factors", {}).values():
                total_score += factor_res.score * factor_res.weight
                total_weight += factor_res.weight
            candidate.final_score = (total_score / total_weight * 100) if total_weight > 0 else 0
            
            if candidate.final_score >= 80:
                candidate.priority_level = "HIGH"
            elif candidate.final_score >= 50:
                candidate.priority_level = "MEDIUM"
            else:
                candidate.priority_level = "LOW"
        return state
""",
    "validate_prioritization.py": """from . import PipelineStage
from typing import Dict, Any

class ValidatePrioritizationStage(PipelineStage):
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Validation logic
        return state
""",
    "resolve_ties.py": """from . import PipelineStage
from typing import Dict, Any

class ResolveTiesStage(PipelineStage):
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Tie-breaker: Evidence > Freshness > Urgency > Impact > stable ID
        def tie_breaker(c):
            f = getattr(c, "factors", {})
            return (
                -c.final_score,
                -f.get("evidence", type('', (), {'score':0})()).score,
                -f.get("freshness", type('', (), {'score':0})()).score,
                -f.get("urgency", type('', (), {'score':0})()).score,
                -f.get("impact", type('', (), {'score':0})()).score,
                getattr(c, "id", "")
            )
        state["candidates"].sort(key=tie_breaker)
        return state
""",
    "generate_result.py": """from . import PipelineStage
from typing import Dict, Any

class RecommendationPrioritizationResult:
    def __init__(self, candidates):
        self.candidates = candidates
        self.diagnostic_info = "success"

class GenerateResultStage(PipelineStage):
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        state["result"] = RecommendationPrioritizationResult(state["candidates"])
        return state
"""
}

for name, code in stages_code.items():
    with open(os.path.join(base_dir, "stages", name), "w", encoding="utf-8") as f:
        f.write(code)

print("Created all files.")
