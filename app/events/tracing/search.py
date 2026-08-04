"""
HunterOS Engage — Distributed Trace Search Engine
app/events/tracing/search.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.storage import AbstractTraceStorage


@dataclass
class TraceSearchQuery:
    """Multi-criteria search query for trace discovery and root cause analysis."""

    trace_id: Optional[str] = None
    event_id: Optional[str] = None
    workspace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    dispatcher_id: Optional[str] = None
    worker_id: Optional[str] = None
    consumer_name: Optional[str] = None
    partition_key: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    start_time_gte: Optional[datetime] = None
    start_time_lte: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


@dataclass
class TraceSearchResult:
    """Paginated search response containing matching trace summaries."""

    total: int
    limit: int
    offset: int
    traces: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "count": len(self.traces),
            "traces": self.traces,
        }


class AbstractTraceSearchEngine(ABC):
    """Abstract interface for querying trace repositories."""

    @abstractmethod
    def search(self, query: TraceSearchQuery) -> TraceSearchResult:
        """Executes a multi-parameter search query."""
        pass


class DefaultTraceSearchEngine(AbstractTraceSearchEngine):
    """
    Standard in-memory trace search engine.
    Supports index-accelerated and linear multi-predicate filtering.
    """

    def __init__(self, storage: AbstractTraceStorage) -> None:
        self._storage = storage

    def search(self, query: TraceSearchQuery) -> TraceSearchResult:
        # Fast path 1: direct trace_id lookup
        if query.trace_id:
            snapshot = self._storage.get_trace(query.trace_id)
            if snapshot and self._matches(snapshot, query):
                return TraceSearchResult(
                    total=1,
                    limit=query.limit,
                    offset=query.offset,
                    traces=[self._summarize(snapshot)],
                )
            return TraceSearchResult(total=0, limit=query.limit, offset=query.offset, traces=[])

        # Fast path 2: direct event_id lookup
        if query.event_id:
            snapshot = self._storage.get_trace_by_event_id(query.event_id)
            if snapshot and self._matches(snapshot, query):
                return TraceSearchResult(
                    total=1,
                    limit=query.limit,
                    offset=query.offset,
                    traces=[self._summarize(snapshot)],
                )
            return TraceSearchResult(total=0, limit=query.limit, offset=query.offset, traces=[])

        # General scan over stored traces
        all_traces = self._storage.list_traces(limit=100000, offset=0)
        matching: List[TraceSnapshot] = []

        for trace in all_traces:
            if self._matches(trace, query):
                matching.append(trace)

        total = len(matching)
        paginated = matching[query.offset : query.offset + query.limit]
        summaries = [self._summarize(t) for t in paginated]

        return TraceSearchResult(
            total=total,
            limit=query.limit,
            offset=query.offset,
            traces=summaries,
        )

    def _matches(self, snapshot: TraceSnapshot, query: TraceSearchQuery) -> bool:
        root = snapshot.root_span
        ctx = root.context if root else None

        # Status check
        if query.status and root and root.status.value != query.status.upper():
            return False

        # Context field checks
        if query.workspace_id and ctx and ctx.workspace_id != query.workspace_id:
            return False
        if query.correlation_id and ctx and ctx.correlation_id != query.correlation_id:
            return False
        if query.causation_id and ctx and ctx.causation_id != query.causation_id:
            return False
        if query.dispatcher_id and ctx and ctx.dispatcher_id != query.dispatcher_id:
            return False
        if query.worker_id and ctx and ctx.worker_id != query.worker_id:
            return False
        if query.consumer_name and ctx and ctx.consumer_name != query.consumer_name:
            # Also check if any child span was executed by this consumer
            if not any(s.metadata.get("consumer_name") == query.consumer_name or s.operation == query.consumer_name for s in snapshot.spans):
                return False
        if query.partition_key and ctx and ctx.partition_key != query.partition_key:
            return False
        if query.priority is not None and ctx and ctx.priority != query.priority:
            return False

        # Duration bounds
        duration = root.duration_ms if root and root.duration_ms is not None else 0.0
        if query.min_duration_ms is not None and duration < query.min_duration_ms:
            return False
        if query.max_duration_ms is not None and duration > query.max_duration_ms:
            return False

        # Time range
        if query.start_time_gte and root and root.start_time < query.start_time_gte:
            return False
        if query.start_time_lte and root and root.start_time > query.start_time_lte:
            return False

        return True

    def _summarize(self, snapshot: TraceSnapshot) -> Dict[str, Any]:
        root = snapshot.root_span
        ctx = root.context if root else None
        return {
            "trace_id": snapshot.trace_id,
            "status": root.status.value if root else "UNKNOWN",
            "start_time": root.start_time.isoformat() if root else None,
            "end_time": root.end_time.isoformat() if root and root.end_time else None,
            "duration_ms": round(root.duration_ms, 3) if root and root.duration_ms is not None else None,
            "total_spans": len(snapshot.spans),
            "event_id": ctx.event_id if ctx else None,
            "workspace_id": ctx.workspace_id if ctx else None,
            "correlation_id": ctx.correlation_id if ctx else None,
            "partition_key": ctx.partition_key if ctx else None,
            "priority": ctx.priority if ctx else None,
            "critical_path_duration_ms": (
                round(snapshot.timeline.critical_path_duration_ms, 3)
                if snapshot.timeline
                else None
            ),
        }
