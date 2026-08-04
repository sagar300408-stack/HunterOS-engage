"""
HunterOS Engage — Distributed Trace Context & Propagation Model
app/events/tracing/context.py
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


def generate_trace_id() -> str:
    """Generates a 32-character hexadecimal W3C compliant trace ID."""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Generates a 16-character hexadecimal W3C compliant span ID."""
    return uuid.uuid4().hex[:16]


@dataclass(frozen=True)
class TraceContext:
    """
    Immutable distributed trace context carried across process, thread, and network boundaries.
    Fully compatible with W3C Trace Context and HunterOS event metadata standards.
    """

    trace_id: str = field(default_factory=generate_trace_id)
    span_id: str = field(default_factory=generate_span_id)
    parent_span_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    event_id: Optional[str] = None
    workspace_id: Optional[str] = None
    dispatcher_id: Optional[str] = None
    worker_id: Optional[str] = None
    consumer_name: Optional[str] = None
    partition_key: Optional[str] = None
    priority: Optional[int] = None
    schema_version: Optional[int] = None
    cluster_epoch: Optional[int] = None
    dispatcher_epoch: Optional[int] = None
    occurred_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def create_child_context(
        self,
        span_id: Optional[str] = None,
        **overrides: Any,
    ) -> "TraceContext":
        """
        Creates an immutable child context with this context's span_id as parent_span_id.
        Preserves trace_id, correlation_id, causation_id, and other context properties unless overridden.
        """
        new_span_id = span_id or generate_span_id()
        params = {
            "trace_id": self.trace_id,
            "span_id": new_span_id,
            "parent_span_id": self.span_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id or self.event_id,
            "event_id": self.event_id,
            "workspace_id": self.workspace_id,
            "dispatcher_id": self.dispatcher_id,
            "worker_id": self.worker_id,
            "consumer_name": self.consumer_name,
            "partition_key": self.partition_key,
            "priority": self.priority,
            "schema_version": self.schema_version,
            "cluster_epoch": self.cluster_epoch,
            "dispatcher_epoch": self.dispatcher_epoch,
            "occurred_at": self.occurred_at,
            "created_at": datetime.now(timezone.utc),
        }
        params.update(overrides)
        return TraceContext(**params)

    def child_context(
        self,
        span_id: Optional[str] = None,
        **overrides: Any,
    ) -> "TraceContext":
        """Alias for create_child_context."""
        return self.create_child_context(span_id=span_id, **overrides)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes context to a dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "event_id": self.event_id,
            "workspace_id": self.workspace_id,
            "dispatcher_id": self.dispatcher_id,
            "worker_id": self.worker_id,
            "consumer_name": self.consumer_name,
            "partition_key": self.partition_key,
            "priority": self.priority,
            "schema_version": self.schema_version,
            "cluster_epoch": self.cluster_epoch,
            "dispatcher_epoch": self.dispatcher_epoch,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_carrier_dict(self) -> Dict[str, str]:
        """
        Encodes context into W3C Trace Context and HunterOS headers for Celery/HTTP transport.
        W3C format: traceparent: 00-{trace_id}-{span_id}-01
        """
        carrier: Dict[str, str] = {
            "traceparent": f"00-{self.trace_id}-{self.span_id}-01",
            "tracestate": f"hunter_ws={self.workspace_id or 'default'}",
            "x-hunter-trace-id": self.trace_id,
            "x-hunter-span-id": self.span_id,
        }
        if self.parent_span_id:
            carrier["x-hunter-parent-span-id"] = self.parent_span_id
        if self.correlation_id:
            carrier["x-hunter-correlation-id"] = str(self.correlation_id)
        if self.causation_id:
            carrier["x-hunter-causation-id"] = str(self.causation_id)
        if self.event_id:
            carrier["x-hunter-event-id"] = str(self.event_id)
        if self.workspace_id:
            carrier["x-hunter-workspace-id"] = str(self.workspace_id)
        if self.dispatcher_id:
            carrier["x-hunter-dispatcher-id"] = str(self.dispatcher_id)
        if self.worker_id:
            carrier["x-hunter-worker-id"] = str(self.worker_id)
        if self.consumer_name:
            carrier["x-hunter-consumer-name"] = str(self.consumer_name)
        if self.partition_key:
            carrier["x-hunter-partition-key"] = str(self.partition_key)
        if self.priority is not None:
            carrier["x-hunter-priority"] = str(self.priority)
        if self.schema_version is not None:
            carrier["x-hunter-schema-version"] = str(self.schema_version)
        if self.cluster_epoch is not None:
            carrier["x-hunter-cluster-epoch"] = str(self.cluster_epoch)
        return carrier

    @classmethod
    def from_carrier_dict(cls, carrier: Dict[str, Any]) -> "TraceContext":
        """
        Extracts TraceContext from incoming headers / metadata carrier dictionary.
        Supports both W3C traceparent and explicit x-hunter-* headers.
        """
        if not carrier:
            return cls()

        trace_id = None
        span_id = None
        parent_span_id = None

        # 1. Parse W3C traceparent (e.g. 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01)
        tp = carrier.get("traceparent") or carrier.get("TRACEPARENT")
        if tp and isinstance(tp, str):
            parts = tp.split("-")
            if len(parts) >= 3:
                trace_id = parts[1]
                parent_span_id = parts[2]
                span_id = generate_span_id()

        trace_id = (
            carrier.get("x-hunter-trace-id")
            or carrier.get("trace_id")
            or trace_id
            or generate_trace_id()
        )
        parent_span_id = (
            carrier.get("x-hunter-parent-span-id")
            or carrier.get("parent_span_id")
            or parent_span_id
        )
        span_id = (
            carrier.get("x-hunter-span-id")
            or carrier.get("span_id")
            or span_id
            or generate_span_id()
        )

        corr_id = carrier.get("x-hunter-correlation-id") or carrier.get("correlation_id")
        caus_id = carrier.get("x-hunter-causation-id") or carrier.get("causation_id")
        evt_id = carrier.get("x-hunter-event-id") or carrier.get("event_id")
        ws_id = carrier.get("x-hunter-workspace-id") or carrier.get("workspace_id")
        disp_id = carrier.get("x-hunter-dispatcher-id") or carrier.get("dispatcher_id")
        wrk_id = carrier.get("x-hunter-worker-id") or carrier.get("worker_id")
        c_name = carrier.get("x-hunter-consumer-name") or carrier.get("consumer_name")
        p_key = carrier.get("x-hunter-partition-key") or carrier.get("partition_key")

        priority_raw = carrier.get("x-hunter-priority") or carrier.get("priority")
        priority = int(priority_raw) if priority_raw is not None else None

        sv_raw = carrier.get("x-hunter-schema-version") or carrier.get("schema_version")
        schema_version = int(sv_raw) if sv_raw is not None else None

        epoch_raw = carrier.get("x-hunter-cluster-epoch") or carrier.get("cluster_epoch")
        cluster_epoch = int(epoch_raw) if epoch_raw is not None else None

        return cls(
            trace_id=str(trace_id),
            span_id=str(span_id),
            parent_span_id=str(parent_span_id) if parent_span_id else None,
            correlation_id=str(corr_id) if corr_id else None,
            causation_id=str(caus_id) if caus_id else None,
            event_id=str(evt_id) if evt_id else None,
            workspace_id=str(ws_id) if ws_id else None,
            dispatcher_id=str(disp_id) if disp_id else None,
            worker_id=str(wrk_id) if wrk_id else None,
            consumer_name=str(c_name) if c_name else None,
            partition_key=str(p_key) if p_key else None,
            priority=priority,
            schema_version=schema_version,
            cluster_epoch=cluster_epoch,
        )
