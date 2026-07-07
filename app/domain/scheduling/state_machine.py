"""
HunterOS Engage — Scheduling State Machine

Enforces valid status transitions for ScheduledEvent.

All status changes MUST go through transition() — never set .status directly.

State diagram:
    pending ──────────────→ confirmed ──→ in_progress ──→ [completed]  ← terminal
      │                        │  ↗ rescheduled ──────────↗
      └────────────────────────┴──────────────────────────→ [cancelled] ← terminal

    rescheduled: original event → rescheduled (terminal-ish),
                 new event created with pending status.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.scheduling.models import ScheduledEvent


# ── Allowed transitions ────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending":     {"confirmed", "cancelled"},
    "confirmed":   {"in_progress", "rescheduled", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "rescheduled": {"cancelled"},      # rescheduled is effectively terminal; new event takes over
    "completed":   set(),               # terminal
    "cancelled":   set(),               # terminal
}


# ── Exception ──────────────────────────────────────────────────────────────────

class InvalidTransitionError(Exception):
    """
    Raised when a status transition is not permitted.
    The API layer catches this and returns HTTP 409 Conflict.
    """
    def __init__(self, from_status: str, to_status: str) -> None:
        self.from_status = from_status
        self.to_status   = to_status
        super().__init__(
            f"Cannot transition event from '{from_status}' to '{to_status}'. "
            f"Allowed from '{from_status}': {VALID_TRANSITIONS.get(from_status, set())}"
        )


# ── Transition function ────────────────────────────────────────────────────────

def transition(event: "ScheduledEvent", new_status: str) -> "ScheduledEvent":
    """
    Validate and apply a status transition to a ScheduledEvent.

    Args:
        event:      The ORM event object (not yet committed).
        new_status: Target status string.

    Returns:
        The same event object with .status updated.

    Raises:
        InvalidTransitionError: If the transition is not in VALID_TRANSITIONS.
    """
    current = event.status
    allowed = VALID_TRANSITIONS.get(current, set())

    if new_status not in allowed:
        raise InvalidTransitionError(current, new_status)

    event.status = new_status
    return event


def can_transition(current_status: str, target_status: str) -> bool:
    """Pure predicate — returns True if the transition is allowed."""
    return target_status in VALID_TRANSITIONS.get(current_status, set())


def get_allowed_transitions(current_status: str) -> set[str]:
    """Return the set of valid target statuses from the given status."""
    return VALID_TRANSITIONS.get(current_status, set())
