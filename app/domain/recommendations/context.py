from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

@dataclass(frozen=True)
class RecommendationContext:
    """
    Context for recommendation generation.
    Holds IMMUTABLE REFERENCES/DTOs pointing to upstream intelligence contexts
    (Memory, Conversation, Intent, Journey).
    This does NOT actively query upstream APIs.
    """
    workspace_id: UUID
    memory_references: List[str] = field(default_factory=list)
    conversation_references: List[str] = field(default_factory=list)
    intent_references: List[str] = field(default_factory=list)
    journey_references: List[str] = field(default_factory=list)
    extracted_features: Dict[str, Any] = field(default_factory=dict)
