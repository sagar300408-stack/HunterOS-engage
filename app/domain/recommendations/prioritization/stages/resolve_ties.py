from . import PipelineStage
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
