"""
HunterOS Engage — Trace Snapshot & Export Model
app/events/tracing/snapshot.py
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

from app.events.tracing.latency import LatencyBreakdown
from app.events.tracing.span import Span
from app.events.tracing.timeline import ExecutionTimeline


@dataclass
class TraceSnapshot:
    """
    Complete, self-contained snapshot of a distributed trace.
    Provides execution tree, latency breakdown, timeline, critical path,
    retry/replay records, and JSON export serialization.
    """

    trace_id: str
    root_span: Span
    spans: List[Span] = field(default_factory=list)
    span_tree: Dict[str, Any] = field(default_factory=dict)
    timeline: Optional[ExecutionTimeline] = None
    latency_breakdown: Optional[LatencyBreakdown] = None
    critical_path_spans: List[str] = field(default_factory=list)
    component_durations_ms: Dict[str, float] = field(default_factory=dict)
    retry_history: List[Dict[str, Any]] = field(default_factory=list)
    replay_history: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    resource_summary: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the trace snapshot into a dictionary suitable for API responses & JSON."""
        return {
            "trace_id": self.trace_id,
            "status": self.root_span.status.value if self.root_span else "UNKNOWN",
            "start_time": self.root_span.start_time.isoformat() if self.root_span else None,
            "end_time": self.root_span.end_time.isoformat() if self.root_span and self.root_span.end_time else None,
            "duration_ms": round(self.root_span.duration_ms, 3) if self.root_span and self.root_span.duration_ms is not None else None,
            "total_spans": len(self.spans),
            "context": self.root_span.context.to_dict() if self.root_span and self.root_span.context else None,
            "span_tree": self.span_tree or (self.root_span.to_tree_dict() if self.root_span else {}),
            "timeline": self.timeline.to_dict() if self.timeline else None,
            "latency_breakdown": self.latency_breakdown.to_dict() if self.latency_breakdown else None,
            "critical_path_spans": self.critical_path_spans,
            "component_durations_ms": {k: round(v, 3) for k, v in self.component_durations_ms.items()},
            "retry_history": self.retry_history,
            "replay_history": self.replay_history,
            "errors": self.errors,
            "warnings": self.warnings,
            "resource_summary": self.resource_summary,
            "created_at": self.created_at.isoformat(),
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serializes the trace snapshot to a JSON formatted string."""
        return json.dumps(self.to_dict(), indent=indent)
