"""
Pydantic schemas for the Customer Memory domain.

Structured memory uses confidence scores throughout.
All downstream consumers (AI context builder, API) use these schemas —
never raw ORM models.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Confidence-scored field types ─────────────────────────────────────────────

class ConfidenceValue(BaseModel):
    """A single extracted fact with its confidence score (0.0 – 1.0)."""
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


class StructuredMemoryData(BaseModel):
    """
    Typed view of the JSONB structured_data column.

    Confidence tiers:
        >= 0.85  → injected directly into AI context
        0.60–0.84 → stored, available for confirmation prompts (Phase 3+)
        < 0.60   → stored but excluded from AI context
    """
    budget: Optional[ConfidenceValue] = None
    timeline: Optional[ConfidenceValue] = None
    preferred_location: Optional[ConfidenceValue] = None
    interests: list[ConfidenceValue] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ── Read schemas ──────────────────────────────────────────────────────────────

class CustomerMemorySchema(BaseModel):
    """Full memory read model."""

    id: UUID
    customer_id: UUID
    summary: Optional[str] = None
    structured_data: Optional[dict[str, Any]] = None
    message_count: int = 0
    last_updated: datetime

    class Config:
        from_attributes = True


class CustomerMemoryVersionSchema(BaseModel):
    """Immutable memory snapshot read model."""

    id: UUID
    customer_id: UUID
    summary: Optional[str] = None
    structured_data: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryEventSchema(BaseModel):
    """Memory event log read model."""

    id: UUID
    customer_id: UUID
    event_type: str
    payload: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Internal DTOs ─────────────────────────────────────────────────────────────

class UpdateMemoryDTO(BaseModel):
    """
    Carries the AI extraction result to update_customer_memory().
    The service validates confidence before writing to the DB.
    """
    summary: str
    structured_data: dict[str, Any] = Field(default_factory=dict)
    trigger: str = "interval"   # "interval" | "significant_fact"
