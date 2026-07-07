"""
HunterOS Engage — Scheduling Metadata Accessors

Typed Pydantic models per event type.

Instead of accessing event.metadata["property_id"] (raw dict),
use event.get_typed_metadata() which returns the correct typed model.

Extending:
    1. Add a new Pydantic class (e.g. InspectionMetadata)
    2. Add it to METADATA_REGISTRY
    That is all — zero other changes needed.
"""

from typing import Optional
from pydantic import BaseModel


# ── Per-type metadata schemas ──────────────────────────────────────────────────

class SiteVisitMetadata(BaseModel):
    """Metadata for site_visit events."""
    property_id: Optional[int]   = None
    location:    Optional[str]   = None
    agent_name:  Optional[str]   = None
    virtual:     bool            = False
    address:     Optional[str]   = None

    model_config = {"extra": "allow"}


class MeetingMetadata(BaseModel):
    """Metadata for meeting events."""
    meeting_type:     Optional[str] = None   # online | in_person | phone
    meeting_link:     Optional[str] = None
    duration_minutes: Optional[int] = None
    agenda:           Optional[str] = None
    platform:         Optional[str] = None   # Zoom | Google Meet | Teams

    model_config = {"extra": "allow"}


class CallbackMetadata(BaseModel):
    """Metadata for callback events."""
    preferred_time: Optional[str] = None   # e.g. "18:00" or "after 6 PM"
    phone:          Optional[str] = None
    reason:         Optional[str] = None

    model_config = {"extra": "allow"}


class FollowUpMetadata(BaseModel):
    """Metadata for followup events."""
    follow_up_reason:         Optional[str] = None
    previous_event_id:        Optional[str] = None
    buying_stage_at_creation: Optional[str] = None

    model_config = {"extra": "allow"}


class ReminderMetadata(BaseModel):
    """Metadata for reminder events."""
    reminder_message: Optional[str] = None
    channel:          Optional[str] = None   # whatsapp | email | sms

    model_config = {"extra": "allow"}


class TaskMetadata(BaseModel):
    """Metadata for task events."""
    task_description: Optional[str] = None
    task_priority:    Optional[str] = None   # high | medium | low
    department:       Optional[str] = None   # sales | support | management

    model_config = {"extra": "allow"}


class GenericMetadata(BaseModel):
    """Fallback for unknown event types — accepts any fields."""
    model_config = {"extra": "allow"}


# ── Registry ───────────────────────────────────────────────────────────────────

METADATA_REGISTRY: dict[str, type[BaseModel]] = {
    "site_visit": SiteVisitMetadata,
    "meeting":    MeetingMetadata,
    "callback":   CallbackMetadata,
    "followup":   FollowUpMetadata,
    "reminder":   ReminderMetadata,
    "task":       TaskMetadata,
}


def parse_metadata(event_type: str, raw: dict) -> BaseModel:
    """
    Return a typed metadata model for the given event type.

    Falls back to GenericMetadata for unknown event types —
    never raises on unknown types.
    """
    cls = METADATA_REGISTRY.get(event_type, GenericMetadata)
    try:
        return cls(**raw)
    except Exception:
        # If metadata doesn't match schema (e.g. bad data), return empty model
        return cls()


def metadata_to_dict(typed: BaseModel) -> dict:
    """Serialize a typed metadata model back to a plain dict for DB storage."""
    return typed.model_dump(exclude_none=True)
