from . import PipelineStage
from typing import Dict, Any

class NormalizeCandidatesStage(PipelineStage):
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Normalize
        return state
