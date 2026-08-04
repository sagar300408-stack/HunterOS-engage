"""
HunterOS Engage — Execution Timeline Engine & Critical Path Analysis
app/events/tracing/timeline.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.events.tracing.span import Span, SpanStatus


@dataclass(frozen=True)
class TimelineSpanEntry:
    """A point-in-time timeline event (span start, span end, or state transition)."""

    timestamp: datetime
    entry_type: str  # "SPAN_START" | "SPAN_END" | "STATE_TRANSITION" | "RETRY" | "REPLAY"
    span_id: str
    component: str
    operation: str
    status: str
    duration_ms: Optional[float] = None
    detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "entry_type": self.entry_type,
            "span_id": self.span_id,
            "component": self.component,
            "operation": self.operation,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 3) if self.duration_ms is not None else None,
            "detail": self.detail,
        }


@dataclass
class ExecutionTimeline:
    """
    Detailed chronological execution breakdown of a trace across platform components.
    """

    trace_id: str
    total_duration_ms: float = 0.0
    entries: List[TimelineSpanEntry] = field(default_factory=list)
    component_timelines: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    critical_path_span_ids: List[str] = field(default_factory=list)
    critical_path_duration_ms: float = 0.0
    blocking_time_ms: float = 0.0
    queue_wait_ms: float = 0.0
    dispatcher_wait_ms: float = 0.0
    worker_wait_ms: float = 0.0
    execution_wait_ms: float = 0.0
    retry_delays_ms: float = 0.0
    replay_chain: List[str] = field(default_factory=list)
    lifecycle_transitions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "total_duration_ms": round(self.total_duration_ms, 3),
            "critical_path_duration_ms": round(self.critical_path_duration_ms, 3),
            "critical_path_span_ids": self.critical_path_span_ids,
            "blocking_time_ms": round(self.blocking_time_ms, 3),
            "queue_wait_ms": round(self.queue_wait_ms, 3),
            "dispatcher_wait_ms": round(self.dispatcher_wait_ms, 3),
            "worker_wait_ms": round(self.worker_wait_ms, 3),
            "execution_wait_ms": round(self.execution_wait_ms, 3),
            "retry_delays_ms": round(self.retry_delays_ms, 3),
            "replay_chain": self.replay_chain,
            "entries_count": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
            "component_timelines": self.component_timelines,
            "lifecycle_transitions": self.lifecycle_transitions,
        }


class AbstractTimelineBuilder(ABC):
    """Abstract interface for constructing execution timelines from trace spans."""

    @abstractmethod
    def build_timeline(
        self,
        trace_id: str,
        spans: List[Span],
        root_span: Optional[Span] = None,
    ) -> ExecutionTimeline:
        """Constructs an ExecutionTimeline from a collection of spans."""
        pass


class DefaultTimelineBuilder(AbstractTimelineBuilder):
    """
    Standard production-grade timeline builder and critical path analyzer.
    Computes exact chronological ordering, parallel vs sequential bottlenecks,
    and stage-based critical paths.
    """

    def build_timeline(
        self,
        trace_id: str,
        spans: List[Span],
        root_span: Optional[Span] = None,
    ) -> ExecutionTimeline:
        if not spans:
            return ExecutionTimeline(trace_id=trace_id)

        # 1. Flatten all spans (including nested children if passed as tree)
        all_spans_map: Dict[str, Span] = {}
        for s in spans:
            self._collect_spans(s, all_spans_map)
        flat_spans = list(all_spans_map.values())

        # 2. Build chronological entries
        entries: List[TimelineSpanEntry] = []
        component_timelines: Dict[str, List[Dict[str, Any]]] = {}
        lifecycle_transitions: List[Dict[str, Any]] = []
        retry_delays_ms = 0.0
        replay_chain: List[str] = []

        min_start = min(s.start_time for s in flat_spans)
        max_end = max((s.end_time or s.start_time) for s in flat_spans)
        total_duration_ms = max(0.0, (max_end - min_start).total_seconds() * 1000.0)

        for s in flat_spans:
            # Start entry
            entries.append(
                TimelineSpanEntry(
                    timestamp=s.start_time,
                    entry_type="SPAN_START",
                    span_id=s.span_id,
                    component=s.component,
                    operation=s.operation,
                    status="RUNNING",
                    detail=f"Started {s.component}.{s.operation}",
                )
            )

            # End entry if finished
            if s.end_time:
                entries.append(
                    TimelineSpanEntry(
                        timestamp=s.end_time,
                        entry_type="SPAN_END",
                        span_id=s.span_id,
                        component=s.component,
                        operation=s.operation,
                        status=s.status.value,
                        duration_ms=s.duration_ms,
                        detail=s.error or f"Completed {s.component}.{s.operation}",
                    )
                )

            # Component timelines
            if s.component not in component_timelines:
                component_timelines[s.component] = []
            component_timelines[s.component].append(s.to_dict())

            # Check for lifecycle, retry, replay markers in metadata
            if s.operation == "lifecycle_transition" or "lifecycle_state" in s.metadata:
                lifecycle_transitions.append(
                    {
                        "span_id": s.span_id,
                        "timestamp": s.start_time.isoformat(),
                        "state": s.metadata.get("lifecycle_state", s.operation),
                        "from_state": s.metadata.get("from_state"),
                        "to_state": s.metadata.get("to_state"),
                    }
                )

            if "retry_delay_seconds" in s.metadata:
                retry_delays_ms += float(s.metadata["retry_delay_seconds"]) * 1000.0

            if "original_event_id" in s.metadata or s.operation == "replay_execution":
                replay_chain.append(s.span_id)

        # Sort entries chronologically
        entries.sort(key=lambda e: e.timestamp)

        # 3. Critical Path Calculation
        critical_path_ids, critical_duration = self._compute_critical_path(flat_spans, root_span)

        # 4. Latency / Wait Time Estimations
        queue_wait_ms = 0.0
        worker_wait_ms = 0.0
        dispatcher_wait_ms = 0.0

        for s in flat_spans:
            if s.operation in ("celery_enqueue", "outbox_poll", "queue_wait"):
                queue_wait_ms += (s.duration_ms or 0.0)
            elif s.operation in ("worker_dequeue", "worker_wait"):
                worker_wait_ms += (s.duration_ms or 0.0)
            elif s.component == "dispatcher":
                dispatcher_wait_ms += (s.duration_ms or 0.0)

        blocking_time = sum(
            s.duration_ms or 0.0
            for s in flat_spans
            if s.metadata.get("policy") == "ORDERED" or s.operation in ("partition_lock_acquire", "schema_upgrade")
        )

        return ExecutionTimeline(
            trace_id=trace_id,
            total_duration_ms=total_duration_ms,
            entries=entries,
            component_timelines=component_timelines,
            critical_path_span_ids=critical_path_ids,
            critical_path_duration_ms=critical_duration,
            blocking_time_ms=blocking_time,
            queue_wait_ms=queue_wait_ms,
            dispatcher_wait_ms=dispatcher_wait_ms,
            worker_wait_ms=worker_wait_ms,
            execution_wait_ms=max(0.0, total_duration_ms - critical_duration),
            retry_delays_ms=retry_delays_ms,
            replay_chain=replay_chain,
            lifecycle_transitions=lifecycle_transitions,
        )

    def _collect_spans(self, span: Span, out_map: Dict[str, Span]) -> None:
        if span.span_id not in out_map:
            out_map[span.span_id] = span
            for c in span.children:
                self._collect_spans(c, out_map)

    def _compute_critical_path(
        self,
        spans: List[Span],
        root_span: Optional[Span],
    ) -> tuple[List[str], float]:
        """
        Computes the critical path (longest sequential path) through the span dependency tree.
        """
        if not spans:
            return [], 0.0

        # Build parent-child graph
        children_map: Dict[Optional[str], List[Span]] = {}
        for s in spans:
            p_id = s.parent_span_id
            if p_id not in children_map:
                children_map[p_id] = []
            children_map[p_id].append(s)

        # Roots are spans with no parent or parent not in this trace
        known_ids = {s.span_id for s in spans}
        roots = [s for s in spans if s.parent_span_id is None or s.parent_span_id not in known_ids]

        if root_span and root_span in spans:
            roots = [root_span]

        memo: Dict[str, tuple[List[str], float]] = {}

        def get_longest_path(span: Span) -> tuple[List[str], float]:
            if span.span_id in memo:
                return memo[span.span_id]

            self_duration = span.duration_ms or 0.0
            children = children_map.get(span.span_id, [])

            if not children:
                res = ([span.span_id], self_duration)
                memo[span.span_id] = res
                return res

            best_child_path: List[str] = []
            best_child_duration: float = 0.0

            for child in children:
                c_path, c_dur = get_longest_path(child)
                if c_dur > best_child_duration:
                    best_child_duration = c_dur
                    best_child_path = c_path

            res = ([span.span_id] + best_child_path, self_duration + best_child_duration)
            memo[span.span_id] = res
            return res

        best_overall_path: List[str] = []
        best_overall_duration: float = 0.0

        for r in roots:
            path, dur = get_longest_path(r)
            if dur >= best_overall_duration:
                best_overall_duration = dur
                best_overall_path = path

        return best_overall_path, best_overall_duration
