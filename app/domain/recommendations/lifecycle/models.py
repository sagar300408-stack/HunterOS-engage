from __future__ import annotations
import enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

class RecommendationLifecycleState(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"
    FULFILLED = "FULFILLED"

@dataclass(frozen=True)
class RecommendationLifecycleTransition:
    from_state: RecommendationLifecycleState
    to_state: RecommendationLifecycleState
    timestamp: datetime
    reason: Optional[str] = None
    actor: Optional[str] = None
