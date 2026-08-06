"""
HunterOS Engage V1 - Canonical Intent Models
Normalized canonical intent representations decouple detection variations from classification logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CanonicalPayload(BaseModel):
    """Normalized payload attributes extracted from evidence or intent parameters."""
    model_config = ConfigDict(frozen=True)

    intent_type_raw: str = "UNKNOWN"
    category_raw: Optional[str] = None
    importance_raw: Optional[str] = None
    primary_entities: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    provenance_details: Dict[str, Any] = Field(default_factory=dict)


class CanonicalIntent(BaseModel):
    """
    Standardized canonical intent data representation.
    Ensures uniform structure for classification regardless of which detector or rule produced it.
    """
    model_config = ConfigDict(frozen=True)

    canonical_intent_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    original_intent_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    canonical_name: str = ""
    normalized_title: str = ""
    normalized_description: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    payload: CanonicalPayload = Field(default_factory=CanonicalPayload)
    source_detection_method: str = "RULE_BASED"
    evidence_message_ids: List[str] = Field(default_factory=list)
    evidence_event_ids: List[uuid.UUID] = Field(default_factory=list)
    evidence_fact_ids: List[uuid.UUID] = Field(default_factory=list)
    evidence_milestone_ids: List[uuid.UUID] = Field(default_factory=list)
    evidence_moment_ids: List[uuid.UUID] = Field(default_factory=list)
    evidence_insight_ids: List[uuid.UUID] = Field(default_factory=list)
    text_snippets: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_intent_id": str(self.canonical_intent_id),
            "original_intent_id": str(self.original_intent_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "canonical_name": self.canonical_name,
            "normalized_title": self.normalized_title,
            "normalized_description": self.normalized_description,
            "confidence": self.confidence,
            "payload": self.payload.model_dump(),
            "source_detection_method": self.source_detection_method,
            "evidence_message_ids": self.evidence_message_ids,
            "evidence_event_ids": [str(e) for e in self.evidence_event_ids],
            "evidence_fact_ids": [str(f) for f in self.evidence_fact_ids],
            "evidence_milestone_ids": [str(m) for m in self.evidence_milestone_ids],
            "evidence_moment_ids": [str(m) for m in self.evidence_moment_ids],
            "evidence_insight_ids": [str(i) for i in self.evidence_insight_ids],
            "text_snippets": self.text_snippets,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
