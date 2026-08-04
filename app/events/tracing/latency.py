"""
HunterOS Engage — Latency Analysis & Component Contribution Engine
app/events/tracing/latency.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.events.tracing.span import Span
from app.events.tracing.timeline import ExecutionTimeline


@dataclass
class LatencyBreakdown:
    """
    Comprehensive decomposition of latency across platform subsystems and execution stages.
    """

    trace_id: str
    publish_latency_ms: Optional[float] = None
    persist_latency_ms: Optional[float] = None
    queue_latency_ms: Optional[float] = None
    dispatcher_latency_ms: Optional[float] = None
    partition_scheduling_latency_ms: Optional[float] = None
    priority_scheduling_latency_ms: Optional[float] = None
    flow_control_latency_ms: Optional[float] = None
    cluster_coordination_latency_ms: Optional[float] = None
    worker_wait_latency_ms: Optional[float] = None
    consumer_execution_latency_ms: Optional[float] = None
    retry_delay_ms: Optional[float] = None
    replay_delay_ms: Optional[float] = None
    end_to_end_latency_ms: Optional[float] = None
    critical_path_latency_ms: Optional[float] = None
    component_contributions: Dict[str, float] = field(default_factory=dict)
    component_durations_ms: Dict[str, float] = field(default_factory=dict)
    slowest_component: Optional[str] = None
    slowest_operation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "publish_latency_ms": round(self.publish_latency_ms, 3) if self.publish_latency_ms is not None else None,
            "persist_latency_ms": round(self.persist_latency_ms, 3) if self.persist_latency_ms is not None else None,
            "queue_latency_ms": round(self.queue_latency_ms, 3) if self.queue_latency_ms is not None else None,
            "dispatcher_latency_ms": round(self.dispatcher_latency_ms, 3) if self.dispatcher_latency_ms is not None else None,
            "partition_scheduling_latency_ms": round(self.partition_scheduling_latency_ms, 3) if self.partition_scheduling_latency_ms is not None else None,
            "priority_scheduling_latency_ms": round(self.priority_scheduling_latency_ms, 3) if self.priority_scheduling_latency_ms is not None else None,
            "flow_control_latency_ms": round(self.flow_control_latency_ms, 3) if self.flow_control_latency_ms is not None else None,
            "cluster_coordination_latency_ms": round(self.cluster_coordination_latency_ms, 3) if self.cluster_coordination_latency_ms is not None else None,
            "worker_wait_latency_ms": round(self.worker_wait_latency_ms, 3) if self.worker_wait_latency_ms is not None else None,
            "consumer_execution_latency_ms": round(self.consumer_execution_latency_ms, 3) if self.consumer_execution_latency_ms is not None else None,
            "retry_delay_ms": round(self.retry_delay_ms, 3) if self.retry_delay_ms is not None else None,
            "replay_delay_ms": round(self.replay_delay_ms, 3) if self.replay_delay_ms is not None else None,
            "end_to_end_latency_ms": round(self.end_to_end_latency_ms, 3) if self.end_to_end_latency_ms is not None else None,
            "critical_path_latency_ms": round(self.critical_path_latency_ms, 3) if self.critical_path_latency_ms is not None else None,
            "component_contributions": {k: round(v, 2) for k, v in self.component_contributions.items()},
            "component_durations_ms": {k: round(v, 3) for k, v in self.component_durations_ms.items()},
            "slowest_component": self.slowest_component,
            "slowest_operation": self.slowest_operation,
        }


class AbstractLatencyAnalyzer(ABC):
    """Abstract interface for analyzing latency and performance contributions."""

    @abstractmethod
    def analyze_latencies(
        self,
        trace_id: str,
        spans: List[Span],
        timeline: Optional[ExecutionTimeline] = None,
    ) -> LatencyBreakdown:
        """Computes a detailed LatencyBreakdown from trace spans."""
        pass


class DefaultLatencyAnalyzer(AbstractLatencyAnalyzer):
    """
    Standard production-grade latency analyzer.
    Aggregates durations by component and operation, computes percentage contributions,
    and identifies performance hotspots.
    """

    def analyze_latencies(
        self,
        trace_id: str,
        spans: List[Span],
        timeline: Optional[ExecutionTimeline] = None,
    ) -> LatencyBreakdown:
        if not spans:
            return LatencyBreakdown(trace_id=trace_id)

        # Collect flat list of all spans
        all_spans_map: Dict[str, Span] = {}
        for s in spans:
            self._collect_spans(s, all_spans_map)
        flat_spans = list(all_spans_map.values())

        # Durations per component
        component_durations: Dict[str, float] = {}
        operation_durations: Dict[str, float] = {}

        publish_ms = 0.0
        persist_ms = 0.0
        queue_ms = 0.0
        dispatcher_ms = 0.0
        partition_ms = 0.0
        priority_ms = 0.0
        flow_ms = 0.0
        cluster_ms = 0.0
        worker_ms = 0.0
        consumer_ms = 0.0
        retry_ms = 0.0
        replay_ms = 0.0

        for s in flat_spans:
            dur = s.duration_ms or 0.0
            comp = s.component
            op = s.operation

            component_durations[comp] = component_durations.get(comp, 0.0) + dur
            operation_durations[f"{comp}.{op}"] = operation_durations.get(f"{comp}.{op}", 0.0) + dur

            # Map specific operation/component buckets
            if comp in ("event_bus", "bus") or op == "publish":
                publish_ms += dur
            elif comp in ("event_store", "store") or op == "persist":
                persist_ms += dur
            elif comp in ("queue", "celery_queue") or op in ("celery_enqueue", "outbox_poll", "queue_wait", "wait"):
                queue_ms += dur
            elif comp == "dispatcher":
                dispatcher_ms += dur
            elif comp == "partition_scheduler" or op in ("partition_plan", "partition_lock_acquire"):
                partition_ms += dur
            elif comp == "priority_scheduler" or op == "priority_plan":
                priority_ms += dur
            elif comp == "flow_controller" or op == "flow_check":
                flow_ms += dur
            elif comp == "cluster_coordinator" or op in ("cluster_assign", "leader_election"):
                cluster_ms += dur
            elif comp in ("worker", "celery_worker") and op in ("worker_execute", "worker_dequeue", "execute"):
                worker_ms += dur
            elif comp in ("consumer", "consumer_orchestrator") or comp.startswith("consumer.") or op in ("handle_event", "consumer_stage"):
                consumer_ms += dur

            if "retry_delay_seconds" in s.metadata:
                retry_ms += float(s.metadata["retry_delay_seconds"]) * 1000.0
            if op == "replay_execution" or "replay_id" in s.metadata:
                replay_ms += dur

        min_start = min(s.start_time for s in flat_spans)
        max_end = max((s.end_time or s.start_time) for s in flat_spans)
        end_to_end_ms = max(0.0, (max_end - min_start).total_seconds() * 1000.0)

        critical_path_ms = timeline.critical_path_duration_ms if timeline else end_to_end_ms

        # Compute percentage contribution (based on total active component time or end-to-end)
        total_comp_time = sum(component_durations.values())
        contributions: Dict[str, float] = {}
        if total_comp_time > 0:
            for comp, dur in component_durations.items():
                contributions[comp] = (dur / total_comp_time) * 100.0

        slowest_comp = None
        if component_durations:
            slowest_comp = max(component_durations.items(), key=lambda x: x[1])[0]

        slowest_op = None
        if operation_durations:
            slowest_op = max(operation_durations.items(), key=lambda x: x[1])[0]

        return LatencyBreakdown(
            trace_id=trace_id,
            publish_latency_ms=publish_ms or None,
            persist_latency_ms=persist_ms or None,
            queue_latency_ms=queue_ms or None,
            dispatcher_latency_ms=dispatcher_ms or None,
            partition_scheduling_latency_ms=partition_ms or None,
            priority_scheduling_latency_ms=priority_ms or None,
            flow_control_latency_ms=flow_ms or None,
            cluster_coordination_latency_ms=cluster_ms or None,
            worker_wait_latency_ms=worker_ms or None,
            consumer_execution_latency_ms=consumer_ms or None,
            retry_delay_ms=retry_ms or None,
            replay_delay_ms=replay_ms or None,
            end_to_end_latency_ms=end_to_end_ms,
            critical_path_latency_ms=critical_path_ms,
            component_contributions=contributions,
            component_durations_ms=component_durations,
            slowest_component=slowest_comp,
            slowest_operation=slowest_op,
        )

    def _collect_spans(self, span: Span, out_map: Dict[str, Span]) -> None:
        if span.span_id not in out_map:
            out_map[span.span_id] = span
            for c in span.children:
                self._collect_spans(c, out_map)
