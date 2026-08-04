"""
HunterOS Engage — Distributed Span Model & Lifecycle
app/events/tracing/span.py
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.events.tracing.context import TraceContext, generate_span_id


class SpanStatus(str, Enum):
    """Execution status of an individual distributed tracing span."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Span:
    """
    Represents an individual unit of work or phase within an event execution pipeline.
    Supports tree hierarchy, timing computations, contextual metadata, and failure captures.
    """

    span_id: str
    trace_id: str
    component: str
    operation: str
    parent_span_id: Optional[str] = None
    status: SpanStatus = SpanStatus.RUNNING
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    context: Optional[TraceContext] = None
    children: List["Span"] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        component: str,
        operation: str,
        context: Optional[TraceContext] = None,
        parent_span_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> "Span":
        """Factory method to construct a new running Span."""
        ctx = context or TraceContext()
        start = now or datetime.now(timezone.utc)
        s_id = ctx.span_id or generate_span_id()
        p_id = parent_span_id or ctx.parent_span_id

        return cls(
            span_id=s_id,
            trace_id=ctx.trace_id,
            parent_span_id=p_id,
            component=component,
            operation=operation,
            status=SpanStatus.RUNNING,
            start_time=start,
            metadata=dict(metadata or {}),
            context=ctx,
        )

    def finish(
        self,
        now: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Span":
        """Marks the span as successfully completed and calculates its duration."""
        if self.status != SpanStatus.RUNNING:
            return self

        self.end_time = now or datetime.now(timezone.utc)
        self.duration_ms = max(
            0.0,
            (self.end_time - self.start_time).total_seconds() * 1000.0,
        )
        self.status = SpanStatus.SUCCESS
        if metadata:
            self.metadata.update(metadata)
        return self

    def fail(
        self,
        error: Any,
        now: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Span":
        """Marks the span as failed, records the error detail, and calculates duration."""
        self.end_time = now or datetime.now(timezone.utc)
        self.duration_ms = max(
            0.0,
            (self.end_time - self.start_time).total_seconds() * 1000.0,
        )
        self.status = SpanStatus.FAILED
        self.error = str(error) if error else "Unknown error"
        if metadata:
            self.metadata.update(metadata)
        return self

    def cancel(
        self,
        reason: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> "Span":
        """Marks the span as cancelled."""
        self.end_time = now or datetime.now(timezone.utc)
        self.duration_ms = max(
            0.0,
            (self.end_time - self.start_time).total_seconds() * 1000.0,
        )
        self.status = SpanStatus.CANCELLED
        if reason:
            self.metadata["cancellation_reason"] = str(reason)
        return self

    def add_child(self, child: "Span") -> None:
        """Appends a child span to this span's hierarchy."""
        self.children.append(child)

    def create_child(
        self,
        component: str,
        operation: str,
        context: Optional[TraceContext] = None,
        metadata: Optional[Dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> "Span":
        """Convenience method to construct, link, and return a child span."""
        child_ctx = context or (self.context.create_child_context() if self.context else TraceContext(trace_id=self.trace_id, parent_span_id=self.span_id))
        child_span = Span.create(
            component=component,
            operation=operation,
            context=child_ctx,
            parent_span_id=self.span_id,
            metadata=metadata,
            now=now,
        )
        self.add_child(child_span)
        return child_span

    def add_metadata(self, key: str, value: Any) -> None:
        """Adds a single key-value pair to span metadata."""
        self.metadata[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Serializes span data without recursive children."""
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_id": self.trace_id,
            "component": self.component,
            "operation": self.operation,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": round(self.duration_ms, 3) if self.duration_ms is not None else None,
            "error": self.error,
            "metadata": self.metadata,
        }

    def to_tree_dict(self) -> Dict[str, Any]:
        """Serializes span data recursively with its child spans."""
        data = self.to_dict()
        data["children"] = [child.to_tree_dict() for child in self.children]
        return data
