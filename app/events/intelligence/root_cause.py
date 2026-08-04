"""
HunterOS Engage — Root Cause Analyzer
app/events/intelligence/root_cause.py

Analyzes completed TraceSnapshots to isolate the primary failure,
map downstream failure propagation chains, and classify root causes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.models import (
    FailureCategory,
    RootCauseReport,
    SeverityLevel,
)
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import Span, SpanStatus


class AbstractRootCauseAnalyzer(ABC):
    """
    Interface for root cause analyzers.
    """

    @abstractmethod
    def analyze_root_cause(self, snapshot: TraceSnapshot) -> Optional[RootCauseReport]:
        """
        Analyzes a completed trace snapshot and returns a RootCauseReport if a failure occurred.
        Returns None if the trace completed successfully.
        """
        pass


class DefaultRootCauseAnalyzer(AbstractRootCauseAnalyzer):
    """
    Production-grade root cause analyzer.
    Isolates the root failure span using chronological & hierarchical traversal,
    extracts failure propagation chains, and maps downstream impact.
    """

    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or IntelligenceConfig()

    def analyze_root_cause(self, snapshot: TraceSnapshot) -> Optional[RootCauseReport]:
        if not snapshot or not snapshot.root_span:
            return None

        # Check if trace contains any failure or error
        failed_spans = [s for s in snapshot.spans if s.status == SpanStatus.FAILED or s.error]
        if not failed_spans and snapshot.root_span.status != SpanStatus.FAILED:
            return None

        if not failed_spans:
            failed_spans = [snapshot.root_span]

        # Identify origin span:
        # Parent spans that fail because their child failed are propagators.
        # Find all failed spans that are parents of other failed spans.
        parent_span_ids_with_failed_children = {s.parent_span_id for s in failed_spans if s.parent_span_id}
        leaf_failed_spans = [s for s in failed_spans if s.span_id not in parent_span_ids_with_failed_children]

        candidates = leaf_failed_spans if leaf_failed_spans else failed_spans
        # Sort candidates chronologically (by start_time)
        candidates.sort(key=lambda s: s.start_time)
        origin_span = candidates[0]

        # Build sequential failure chain
        failure_chain: List[Dict[str, Any]] = []
        downstream_components: List[str] = []

        # Sort all failed spans chronologically for chain
        failed_spans.sort(key=lambda s: s.start_time)
        for s in failed_spans:
            err_str = str(s.error) if s.error else "Unknown execution failure"
            chain_entry = {
                "span_id": s.span_id,
                "parent_span_id": s.parent_span_id,
                "component": s.component,
                "operation": s.operation,
                "error": err_str,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "duration_ms": s.duration_ms,
            }
            failure_chain.append(chain_entry)

            if s.component != origin_span.component and s.component not in downstream_components:
                downstream_components.append(s.component)

        # Categorize the failure
        error_msg = str(origin_span.error) if origin_span.error else "Execution failure"
        category = self._classify_error(origin_span, error_msg)

        is_retry = bool(
            snapshot.retry_history
            or any("retry" in s.operation.lower() or "retry_delay_seconds" in s.metadata for s in snapshot.spans)
        )
        is_replay = bool(
            snapshot.replay_history
            or any("replay" in s.operation.lower() or "replay_id" in s.metadata for s in snapshot.spans)
        )

        severity = SeverityLevel.CRITICAL if (len(downstream_components) > 2 or is_replay) else SeverityLevel.HIGH

        recommendation = self._generate_recommendation_summary(
            category=category,
            origin_component=origin_span.component,
            origin_operation=origin_span.operation,
        )

        ctx = snapshot.root_span.context
        event_id = ctx.event_id if ctx else None
        workspace_id = ctx.workspace_id if ctx else None

        return RootCauseReport(
            trace_id=snapshot.trace_id,
            event_id=str(event_id) if event_id else None,
            workspace_id=str(workspace_id) if workspace_id else None,
            category=category,
            originating_component=origin_span.component,
            originating_operation=origin_span.operation,
            error_message=error_msg,
            error_type=type(origin_span.error).__name__ if origin_span.error and not isinstance(origin_span.error, str) else "Error",
            primary_failure={
                "span_id": origin_span.span_id,
                "component": origin_span.component,
                "operation": origin_span.operation,
                "metadata": origin_span.metadata,
                "error": error_msg,
            },
            failure_chain=failure_chain,
            downstream_impacted_components=downstream_components,
            is_retry_failure=is_retry,
            is_replay_failure=is_replay,
            recommendation_summary=recommendation,
            severity=severity,
        )

    def _classify_error(self, span: Span, error_msg: str) -> FailureCategory:
        lowered = error_msg.lower()
        comp = span.component.lower()
        op = span.operation.lower()

        if "lock" in lowered or "conflict" in lowered or "contention" in lowered:
            return FailureCategory.LOCK_CONTENTION
        if "timeout" in lowered or "timed out" in lowered or "deadline" in lowered:
            return FailureCategory.TIMEOUT
        if "schema" in lowered or "validation" in lowered or "payload" in lowered:
            return FailureCategory.SCHEMA_MISMATCH
        if "postgres" in lowered or "database" in lowered or "sql" in lowered or "integrity" in lowered or "eventstore" in comp or "store" in comp:
            return FailureCategory.DATABASE_ERROR
        if "connection" in lowered or "network" in lowered or "unreachable" in lowered or "http" in lowered:
            return FailureCategory.NETWORK_FAILURE
        if "queue" in lowered or "backpressure" in lowered or "congestion" in lowered:
            return FailureCategory.QUEUE_CONGESTION
        if "panic" in lowered or "fatal" in lowered or "segmentation" in lowered:
            return FailureCategory.SYSTEM_PANIC
        if "consumer" in comp or "handler" in op or "division" in lowered or "exception" in lowered or "error" in lowered:
            return FailureCategory.CONSUMER_EXCEPTION

        return FailureCategory.UNKNOWN

    def _generate_recommendation_summary(
        self,
        category: FailureCategory,
        origin_component: str,
        origin_operation: str,
    ) -> str:
        if category == FailureCategory.LOCK_CONTENTION:
            return f"Investigate partition key distribution and reduce transaction lock duration in {origin_component}."
        elif category == FailureCategory.TIMEOUT:
            return f"Increase timeout threshold or optimize query/execution latency for {origin_component}.{origin_operation}."
        elif category == FailureCategory.SCHEMA_MISMATCH:
            return f"Verify SchemaRegistry version compatibility and registered schema upgrade adapters for {origin_component}."
        elif category == FailureCategory.DATABASE_ERROR:
            return f"Inspect database connection pool health, lock waits, and disk IOPS for {origin_component}."
        elif category == FailureCategory.CONSUMER_EXCEPTION:
            return f"Debug business logic and payload handling in consumer {origin_component}."
        return f"Inspect detailed error logs and stack traces for {origin_component}.{origin_operation}."
