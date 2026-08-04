"""
HunterOS Engage — Idempotency Decision Model
app/events/idempotency/decision.py

Defines the explicit decision contract produced by the Idempotency Engine
when evaluating an incoming event publication.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class IdempotencyAction(str, Enum):
    """
    Action to be taken by the publisher/store service based on idempotency evaluation.
    """
    PERSIST = "PERSIST"                 # New unique event; proceed with insert
    DUPLICATE = "DUPLICATE"             # Existing event detected; suppress duplicate and return existing
    REPLAY_BYPASS = "REPLAY_BYPASS"     # Replay requested; bypass duplicate suppression and proceed
    RACE_RECOVERED = "RACE_RECOVERED"   # Concurrent race detected and recovered via savepoint rollback


class IdempotencyConflictError(Exception):
    """
    Raised when an insert encounters a unique constraint violation on idempotency_key.
    """
    def __init__(self, idempotency_key: str, message: Optional[str] = None):
        self.idempotency_key = idempotency_key
        super().__init__(message or f"Idempotency conflict for key: {idempotency_key}")


@dataclass
class IdempotencyDecision:
    """
    Structured outcome of an idempotency evaluation.
    """
    action: IdempotencyAction
    key: str
    reason: str
    existing_event: Optional[Any] = None
    lookup_duration_ms: float = 0.0

    @property
    def is_persisted(self) -> bool:
        """True if the event should be or was newly persisted."""
        return self.action in (IdempotencyAction.PERSIST, IdempotencyAction.REPLAY_BYPASS)

    @property
    def is_duplicate(self) -> bool:
        """True if the event was detected as a duplicate (pre-lookup or race-recovered)."""
        return self.action in (IdempotencyAction.DUPLICATE, IdempotencyAction.RACE_RECOVERED)
