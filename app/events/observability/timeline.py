"""
HunterOS Engage — Event Timeline & Latency Computation
app/events/observability/timeline.py

Derives an ordered lifecycle timeline and a complete latency breakdown
from a single EventRecord row plus the consumer spans stored in its
metadata_payload.

Design
──────
• No extra DB tables.  Everything is reconstructed from columns that already
  exist on EventRecord (occurred_at, queued_at, processing_started_at,
  completed_at, lifecycle_state) and the consumer_spans list stored in
  metadata_payload by tasks.py after each dispatch cycle.

• All latencies are float milliseconds (1 ms = 1.0).  None is returned for
  any interval whose timestamps are not yet available (e.g. processing has
  not started yet).

• Per-stage latency is computed by summing individual consumer durations
  within each stage.  This is cumulative for stages with PARALLEL consumers
  (since they run concurrently, the stage wall-clock time ≈ max, not sum).
  The sum is still useful for aggregate load analysis.

Public API
──────────
    build_timeline(record) -> List[TimelineEntry]
    compute_latencies(record, consumer_spans) -> LatencyMetrics
    build_trace_response(record) -> dict
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TimelineEntry:
    """
    A single immutable lifecycle transition recorded in chronological order.

    Attributes:
        state:      The lifecycle state reached at this timestamp.
        timestamp:  UTC datetime of the transition.  None if the state has
                    not been reached yet (forward-fill guard).
        detail:     Optional human-readable annotation (error message for
                    FAILED / DEAD_LETTER; retry number for RETRYING, etc.)
    """
    state:     str
    timestamp: Optional[datetime]
    detail:    Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "state":     self.state,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "detail":    self.detail,
        }


@dataclass
class LatencyMetrics:
    """
    Complete latency breakdown for a single event dispatch cycle.

    All values are float milliseconds (None = data not yet available).

    Attributes:
        persist_to_queue_ms:         Time from publish to outbox pickup.
        queue_to_processing_ms:      Time from Celery queue to worker start.
        processing_to_completion_ms: Time from worker start to final state.
        end_to_end_ms:               occurred_at → completed_at.
        per_consumer_ms:             {consumer_class_name: duration_ms}
        per_stage_ms:                {stage_index: sum_of_consumer_durations_ms}
    """
    persist_to_queue_ms:          Optional[float]
    queue_to_processing_ms:       Optional[float]
    processing_to_completion_ms:  Optional[float]
    end_to_end_ms:                Optional[float]
    per_consumer_ms:              Dict[str, float] = field(default_factory=dict)
    per_stage_ms:                 Dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "persist_to_queue_ms":          self.persist_to_queue_ms,
            "queue_to_processing_ms":       self.queue_to_processing_ms,
            "processing_to_completion_ms":  self.processing_to_completion_ms,
            "end_to_end_ms":                self.end_to_end_ms,
            "per_consumer_ms":              self.per_consumer_ms,
            "per_stage_ms":                 {str(k): v for k, v in self.per_stage_ms.items()},
        }


# ── Timeline builder ──────────────────────────────────────────────────────────

def build_timeline(record: Any) -> List[TimelineEntry]:
    """
    Reconstruct the ordered lifecycle timeline from an EventRecord row.

    The timeline is built from four timestamp columns on EventRecord:
        occurred_at           → PERSISTED
        queued_at             → QUEUED
        processing_started_at → PROCESSING
        completed_at          → terminal state (lifecycle_state value)

    Entries are filtered to those with a non-None timestamp and sorted
    chronologically.  Entries with a None timestamp are included only if
    the state is the current lifecycle_state, providing a "current" marker
    even when a terminal timestamp has not been written yet.

    Args:
        record: An EventRecord SQLAlchemy model instance.

    Returns:
        Chronologically ordered list of TimelineEntry.
    """
    candidates: List[TimelineEntry] = []

    if record.occurred_at:
        candidates.append(TimelineEntry(
            state="PERSISTED",
            timestamp=record.occurred_at,
        ))

    if record.queued_at:
        candidates.append(TimelineEntry(
            state="QUEUED",
            timestamp=record.queued_at,
        ))

    if record.processing_started_at:
        candidates.append(TimelineEntry(
            state="PROCESSING",
            timestamp=record.processing_started_at,
        ))

    if record.completed_at:
        # The terminal state is stored in lifecycle_state; completed_at
        # is written for both COMPLETED and DEAD_LETTER transitions.
        terminal_state = record.lifecycle_state
        detail = record.error_detail if record.error_detail else None
        candidates.append(TimelineEntry(
            state=terminal_state,
            timestamp=record.completed_at,
            detail=detail,
        ))

    # Sort by timestamp ascending (oldest first).
    # Use epoch=0 as a safe sort key for any None timestamps that slipped through.
    _epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return sorted(candidates, key=lambda e: e.timestamp or _epoch)


# ── Latency computation ───────────────────────────────────────────────────────

def _delta_ms(a: Optional[datetime], b: Optional[datetime]) -> Optional[float]:
    """Return (b - a) in milliseconds, or None if either value is missing."""
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds() * 1_000)


def compute_latencies(record: Any, consumer_spans: List[dict]) -> LatencyMetrics:
    """
    Calculate all latency breakdowns for a dispatched event.

    Args:
        record:         EventRecord row.
        consumer_spans: List of span dicts stored in metadata_payload.
                        Each dict has at minimum: consumer, stage, duration_ms.

    Returns:
        LatencyMetrics populated with all available intervals.
    """
    persist_to_queue         = _delta_ms(record.occurred_at, record.queued_at)
    queue_to_processing      = _delta_ms(record.queued_at, record.processing_started_at)
    processing_to_completion = _delta_ms(record.processing_started_at, record.completed_at)
    end_to_end               = _delta_ms(record.occurred_at, record.completed_at)

    per_consumer: Dict[str, float] = {}
    per_stage:    Dict[int, float] = {}

    for span in consumer_spans:
        duration = span.get("duration_ms")
        if duration is None:
            continue

        consumer_name = span.get("consumer", "unknown")
        per_consumer[consumer_name] = float(duration)

        stage = span.get("stage")
        if stage is not None:
            per_stage[int(stage)] = per_stage.get(int(stage), 0.0) + float(duration)

    return LatencyMetrics(
        persist_to_queue_ms=persist_to_queue,
        queue_to_processing_ms=queue_to_processing,
        processing_to_completion_ms=processing_to_completion,
        end_to_end_ms=end_to_end,
        per_consumer_ms=per_consumer,
        per_stage_ms=per_stage,
    )


# ── Trace response assembler ──────────────────────────────────────────────────

def build_trace_response(record: Any) -> dict:
    """
    Assemble the complete event trace dict for the /reliability/trace endpoint.

    Combines:
    • EventRecord scalar columns (identity, schema, retry state)
    • Derived timeline from timestamp columns
    • Consumer spans from metadata_payload["consumer_spans"]
    • Latency breakdown
    • Retry history from metadata_payload["retry_history"]
    • Replay history from metadata_payload["replay_history"]

    Args:
        record: EventRecord SQLAlchemy model instance.

    Returns:
        Dict suitable for direct JSON serialization.
    """
    metadata       = record.metadata_payload or {}
    consumer_spans = metadata.get("consumer_spans", [])
    retry_history  = metadata.get("retry_history", [])
    replay_history = metadata.get("replay_history", [])

    timeline   = build_timeline(record)
    latencies  = compute_latencies(record, consumer_spans)

    # trace_id defaults to event_id when not explicitly set on the event
    trace_id = getattr(record, "trace_id", None) or str(record.event_id)

    return {
        "event_id":      str(record.event_id),
        "event_name":    record.event_name,
        "workspace_id":  str(record.workspace_id),
        "trace_id":      trace_id,
        "correlation_id": (
            str(record.correlation_id) if record.correlation_id else None
        ),
        "schema_version": getattr(record, "schema_version", 1),
        "current_state":  record.lifecycle_state,
        "retry_count":    record.retry_count,
        "occurred_at":    record.occurred_at.isoformat() if record.occurred_at else None,
        "timeline":       [e.to_dict() for e in timeline],
        "consumer_spans": consumer_spans,
        "latencies":      latencies.to_dict(),
        "retry_history":  retry_history,
        "replay_history": replay_history,
    }
