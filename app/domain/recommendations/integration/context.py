from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime

@dataclass
class RecommendationIntegrationPipelineContext:
    pipeline_id: str
    started_at: datetime
    detection_artifact: Optional[Any] = None
    prioritization_artifact: Optional[Any] = None
    explanation_artifact: Optional[Any] = None
    state: str = "INITIALIZED"

    def update_state(self, new_state: str) -> None:
        self.state = new_state
