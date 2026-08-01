"""
HunterOS Engage — Event Lifecycle State

Defines every state an EventRecord can occupy from the moment it is
persisted until it is fully consumed or dead-lettered.

Lifecycle transitions:
  PERSISTED → QUEUED → PROCESSING → COMPLETED
                                  → FAILED (retry)
                                  → DEAD_LETTER (max retries exceeded)
  Any state → REPLAYED (when manually replayed via the reliability API)

Architectural Rule:
  Stage 4 (Persistence) always precedes Stage 5 (Distribution).
  The lifecycle state is the machine-readable proof of this guarantee.
"""

from enum import Enum


class EventLifecycleState(str, Enum):
    """
    Canonical lifecycle states for every EventRecord in HunterOS.

    NEW:         Constructed but not yet written to the event store.
                 This state is transient — never stored to the DB.
    PERSISTED:   Written to event_store within the publishing DB transaction.
                 The event is now a durable, auditable record.
    QUEUED:      A Celery dispatch task has been enqueued for this event.
                 The event will be delivered to consumers.
    PROCESSING:  A Celery worker has picked up the dispatch task and is
                 routing the event to its registered consumers.
    COMPLETED:   All consumers executed (successes and isolated failures logged).
    FAILED:      One or more consumers failed and the dispatch task is
                 awaiting retry. retry_count and next_retry_at are set.
    DEAD_LETTER: Max retries exceeded. Human intervention required.
                 Available for replay via the reliability API.
    REPLAYED:    Event was manually re-dispatched via the reliability API.
                 A new dispatch cycle begins; state will transition to QUEUED.
    """

    NEW = "NEW"
    PERSISTED = "PERSISTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD_LETTER = "DEAD_LETTER"
    REPLAYED = "REPLAYED"


# Valid forward transitions — used to enforce state machine correctness
VALID_TRANSITIONS: dict[EventLifecycleState, set[EventLifecycleState]] = {
    EventLifecycleState.NEW:          {EventLifecycleState.PERSISTED},
    EventLifecycleState.PERSISTED:    {EventLifecycleState.QUEUED},
    EventLifecycleState.QUEUED:       {EventLifecycleState.PROCESSING},
    EventLifecycleState.PROCESSING:   {
        EventLifecycleState.COMPLETED,
        EventLifecycleState.FAILED,
        EventLifecycleState.RETRYING,     # Stale recovery
    },
    EventLifecycleState.FAILED:       {
        EventLifecycleState.RETRYING,     # Under max retries
        EventLifecycleState.DEAD_LETTER,  # Max retries exceeded
    },
    EventLifecycleState.RETRYING:     {EventLifecycleState.QUEUED},
    EventLifecycleState.DEAD_LETTER:  {EventLifecycleState.REPLAYED},
    EventLifecycleState.COMPLETED:    {EventLifecycleState.REPLAYED},
    EventLifecycleState.REPLAYED:     {EventLifecycleState.QUEUED},
}


def can_transition(
    from_state: EventLifecycleState,
    to_state: EventLifecycleState,
) -> bool:
    """Return True if the given state transition is architecturally valid."""
    return to_state in VALID_TRANSITIONS.get(from_state, set())
