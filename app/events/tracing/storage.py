"""
HunterOS Engage — Thread-Safe Distributed Trace Storage & Indexing
app/events/tracing/storage.py
"""

from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional, Set

from app.events.tracing.config import TraceConfig
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import Span


class AbstractTraceStorage(ABC):
    """Abstract interface for trace persistence and indexing engines."""

    @abstractmethod
    def store_active_span(self, span: Span) -> None:
        """Stores or updates an active span within an in-flight trace."""
        pass

    @abstractmethod
    def finish_trace(self, trace_id: str, snapshot: TraceSnapshot) -> None:
        """Finalizes and stores the complete TraceSnapshot."""
        pass

    @abstractmethod
    def get_trace(self, trace_id: str) -> Optional[TraceSnapshot]:
        """Retrieves a completed TraceSnapshot by trace_id."""
        pass

    @abstractmethod
    def get_trace_by_event_id(self, event_id: str) -> Optional[TraceSnapshot]:
        """Retrieves a completed TraceSnapshot by associated event_id."""
        pass

    @abstractmethod
    def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> List[TraceSnapshot]:
        """Lists completed traces with pagination and basic filtering."""
        pass

    @abstractmethod
    def delete_trace(self, trace_id: str) -> bool:
        """Deletes a trace snapshot and removes its secondary indexes."""
        pass

    @abstractmethod
    def cleanup_expired(self, now: Optional[datetime] = None) -> int:
        """Prunes traces exceeding max retention capacity or TTL."""
        pass

    @abstractmethod
    def get_total_traces_count(self) -> int:
        """Returns the total number of currently stored traces."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clears all stored traces and indices (for testing/cleanup)."""
        pass


class DefaultInMemoryTraceStorage(AbstractTraceStorage):
    """
    Thread-safe in-memory trace storage with LRU capacity eviction,
    TTL expiration, and secondary index lookups for event_id, correlation_id, and workspace_id.
    """

    def __init__(self, config: Optional[TraceConfig] = None) -> None:
        self._config = config or TraceConfig()
        self._lock = threading.RLock()

        # In-flight active spans: trace_id -> Dict[span_id, Span]
        self._active_spans: Dict[str, Dict[str, Span]] = {}

        # Completed traces: trace_id -> TraceSnapshot (Ordered by insertion time)
        self._traces: OrderedDict[str, TraceSnapshot] = OrderedDict()

        # Secondary lookup indices
        self._by_event_id: Dict[str, str] = {}
        self._by_correlation_id: Dict[str, Set[str]] = {}
        self._by_workspace_id: Dict[str, Set[str]] = {}
        self._by_partition_key: Dict[str, Set[str]] = {}

    def store_active_span(self, span: Span) -> None:
        with self._lock:
            trace_id = span.trace_id
            if trace_id not in self._active_spans:
                self._active_spans[trace_id] = {}
            self._active_spans[trace_id][span.span_id] = span

    def finish_trace(self, trace_id: str, snapshot: TraceSnapshot) -> None:
        with self._lock:
            # Remove from active map if present
            self._active_spans.pop(trace_id, None)

            # Insert or update completed snapshot
            if trace_id in self._traces:
                del self._traces[trace_id]

            self._traces[trace_id] = snapshot

            # Index by event_id, correlation_id, workspace_id, partition_key
            ctx = snapshot.root_span.context if snapshot.root_span else None
            if ctx:
                if ctx.event_id:
                    self._by_event_id[str(ctx.event_id)] = trace_id
                if ctx.correlation_id:
                    c_id = str(ctx.correlation_id)
                    if c_id not in self._by_correlation_id:
                        self._by_correlation_id[c_id] = set()
                    self._by_correlation_id[c_id].add(trace_id)
                if ctx.workspace_id:
                    w_id = str(ctx.workspace_id)
                    if w_id not in self._by_workspace_id:
                        self._by_workspace_id[w_id] = set()
                    self._by_workspace_id[w_id].add(trace_id)
                if ctx.partition_key:
                    p_key = str(ctx.partition_key)
                    if p_key not in self._by_partition_key:
                        self._by_partition_key[p_key] = set()
                    self._by_partition_key[p_key].add(trace_id)

            # Evict if exceeding max capacity
            while len(self._traces) > self._config.max_trace_retention:
                oldest_trace_id, _ = self._traces.popitem(last=False)
                self._remove_from_indices(oldest_trace_id)

    def get_trace(self, trace_id: str) -> Optional[TraceSnapshot]:
        with self._lock:
            return self._traces.get(trace_id)

    def get_trace_by_event_id(self, event_id: str) -> Optional[TraceSnapshot]:
        with self._lock:
            trace_id = self._by_event_id.get(str(event_id))
            if trace_id:
                return self._traces.get(trace_id)
            return None

    def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> List[TraceSnapshot]:
        with self._lock:
            results: List[TraceSnapshot] = []
            # Return in reverse chronological order (newest first)
            for trace in reversed(self._traces.values()):
                if status and trace.root_span and trace.root_span.status.value != status:
                    continue
                if workspace_id:
                    ctx = trace.root_span.context if trace.root_span else None
                    if not ctx or ctx.workspace_id != workspace_id:
                        continue
                results.append(trace)

            return results[offset : offset + limit]

    def delete_trace(self, trace_id: str) -> bool:
        with self._lock:
            self._active_spans.pop(trace_id, None)
            if trace_id in self._traces:
                del self._traces[trace_id]
                self._remove_from_indices(trace_id)
                return True
            return False

    def cleanup_expired(self, now: Optional[datetime] = None) -> int:
        with self._lock:
            current_time = now or datetime.now(timezone.utc)
            ttl = self._config.retention_ttl_seconds
            expired_ids: List[str] = []

            for trace_id, snapshot in self._traces.items():
                age_seconds = (current_time - snapshot.created_at).total_seconds()
                if age_seconds > ttl:
                    expired_ids.append(trace_id)

            for trace_id in expired_ids:
                if trace_id in self._traces:
                    del self._traces[trace_id]
                    self._remove_from_indices(trace_id)

            return len(expired_ids)

    def get_total_traces_count(self) -> int:
        with self._lock:
            return len(self._traces)

    def clear(self) -> None:
        with self._lock:
            self._active_spans.clear()
            self._traces.clear()
            self._by_event_id.clear()
            self._by_correlation_id.clear()
            self._by_workspace_id.clear()
            self._by_partition_key.clear()

    def _remove_from_indices(self, trace_id: str) -> None:
        """Removes trace_id from secondary index dictionaries."""
        # Clean event_id map
        ev_keys = [k for k, v in self._by_event_id.items() if v == trace_id]
        for k in ev_keys:
            del self._by_event_id[k]

        # Clean correlation_id map
        for s in self._by_correlation_id.values():
            s.discard(trace_id)

        # Clean workspace_id map
        for s in self._by_workspace_id.values():
            s.discard(trace_id)

        # Clean partition_key map
        for s in self._by_partition_key.values():
            s.discard(trace_id)
