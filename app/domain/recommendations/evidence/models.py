from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from uuid import UUID

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class EvidenceType(str, Enum):
    MEMORY = "MEMORY"
    CONVERSATION = "CONVERSATION"
    INTENT = "INTENT"
    JOURNEY = "JOURNEY"
    EVENT = "EVENT"
    TIMELINE = "TIMELINE"
    USER_INPUT = "USER_INPUT"
    SYSTEM_CONTEXT = "SYSTEM_CONTEXT"
    EXTERNAL = "EXTERNAL"
    CUSTOM = "CUSTOM"

@dataclass(frozen=True)
class EvidenceReference:
    reference_id: str
    reference_type: str
    url: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class RecommendationEvidence:
    id: UUID
    recommendation_id: UUID
    type: EvidenceType
    reference: EvidenceReference
    relevance_score: float
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self):
        if not (0.0 <= self.relevance_score <= 1.0):
            raise ValueError("Relevance score must be between 0.0 and 1.0")
