"""
HunterOS Engage — Scheduling Validators

Validation logic for event creation and metadata.

Design:
  - Returns list[str] of error messages (empty = valid)
  - Never raises — callers decide whether to reject or warn
  - Reads required fields from EVENT_REQUIREMENTS in resolver.py
"""

from datetime import datetime
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Required metadata fields per event type
# These must be present in metadata (or as dedicated columns) for the event to be "complete"
EVENT_REQUIRED_METADATA: dict[str, list[str]] = {
    "site_visit": ["location"],
    "meeting":    [],
    "callback":   ["preferred_time"],
    "followup":   [],
    "reminder":   ["reminder_message"],
    "task":       ["task_description"],
}

VALID_EVENT_TYPES = set(EVENT_REQUIRED_METADATA.keys())
VALID_STATUSES    = {"pending", "confirmed", "in_progress", "completed", "cancelled", "rescheduled"}
VALID_PRIORITIES  = {"high", "medium", "low"}


def validate_create_event(
    event_type:    str,
    title:         str,
    metadata:      Optional[dict]     = None,
    scheduled_for: Optional[datetime] = None,
    priority:      Optional[str]      = None,
) -> list[str]:
    """
    Validate fields required to create a ScheduledEvent.

    Returns a list of error strings. Empty list means valid.
    """
    errors: list[str] = []

    if not event_type:
        errors.append("event_type is required")
    elif event_type not in VALID_EVENT_TYPES:
        errors.append(
            f"Unknown event_type '{event_type}'. "
            f"Valid types: {sorted(VALID_EVENT_TYPES)}"
        )

    if not title or not title.strip():
        errors.append("title is required and cannot be blank")

    if priority and priority not in VALID_PRIORITIES:
        errors.append(f"Invalid priority '{priority}'. Valid: {sorted(VALID_PRIORITIES)}")

    if scheduled_for and scheduled_for.tzinfo is None:
        errors.append("scheduled_for must be timezone-aware")

    return errors


def validate_metadata_completeness(
    event_type: str,
    metadata:   Optional[dict] = None,
) -> list[str]:
    """
    Check that all required metadata fields for this event type are present.

    Used by the candidate promotion flow to determine if a candidate is ready.
    Returns empty list if complete.
    """
    meta     = metadata or {}
    required = EVENT_REQUIRED_METADATA.get(event_type, [])
    missing  = [f for f in required if not meta.get(f)]
    return missing


def get_missing_fields(event_type: str, collected: dict) -> list[str]:
    """
    Return the list of required fields not yet collected.
    Used by the candidate service to track progress.
    """
    return validate_metadata_completeness(event_type, collected)
