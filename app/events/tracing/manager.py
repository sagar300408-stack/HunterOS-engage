"""
HunterOS Engage — Distributed Trace Manager & Execution Coordinator
app/events/tracing/manager.py
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
import contextvars
from datetime import datetime, timezone
import logging
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

from app.events.observability.metrics import event_metrics
from app.events.tracing.config import TraceConfig
from app.events.tracing.context import TraceContext, generate_span_id, generate_trace_id
from app.events.tracing.latency import AbstractLatencyAnalyzer, DefaultLatencyAnalyzer
from app.events.tracing.search import AbstractTraceSearchEngine, DefaultTraceSearchEngine, TraceSearchQuery, TraceSearchResult
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import Span, SpanStatus
from app.events.tracing.storage import AbstractTraceStorage, DefaultInMemoryTraceStorage
from app.events.tracing.timeline import AbstractTimelineBuilder, DefaultTimelineBuilder

logger = logging.getLogger("hunter.tracing")

# ContextVar for active span in current thread/async task
_CURRENT_SPAN: contextvars.ContextVar[Optional[Span]] = contextvars.ContextVar("hunter_current_span", default=None)
_CURRENT_CONTEXT: contextvars.ContextVar[Optional[TraceContext]] = contextvars.ContextVar("hunter_current_context", default=None)


class AbstractTraceManager(ABC):
    """Abstract interface for the Distributed Trace Manager."""

    @abstractmethod
    def start_trace(
        self,
        component: str,
        operation: str,
        context: Optional[TraceContext] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Starts a new root trace span and establishes active context."""
        pass

    @abstractmethod
    def start_span(
        self,
        component: str,
        operation: str,
        context: Optional[TraceContext] = None,
        parent_span: Optional[Span] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Starts a child or independent span."""
        pass

    @abstractmethod
    def finish_span(
        self,
        span: Span,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[Any] = None,
    ) -> Span:
        """Finishes a span, updating state and attaching metadata or error details."""
        pass

    @abstractmethod
    def finish_trace(
        self,
        root_span: Span,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[Any] = None,
    ) -> Optional[TraceSnapshot]:
        """Finalizes the entire trace, builds timeline, analyzes latency, and persists snapshot."""
        pass

    @abstractmethod
    def get_current_span(self) -> Optional[Span]:
        """Returns the currently active span in the current async/thread context."""
        pass

    @abstractmethod
    def get_current_context(self) -> Optional[TraceContext]:
        """Returns the currently active TraceContext in the current async/thread context."""
        pass

    @abstractmethod
    def get_trace(self, trace_id: str) -> Optional[TraceSnapshot]:
        """Retrieves a completed trace snapshot."""
        pass

    @abstractmethod
    def search_traces(self, query: TraceSearchQuery) -> TraceSearchResult:
        """Searches traces."""
        pass


class DefaultTraceManager(AbstractTraceManager):
    """
    Production-grade distributed trace manager for HunterOS Engage.
    Fully passive, thread-safe, async-safe, and fail-isolated.
    """

    def __init__(
        self,
        config: Optional[TraceConfig] = None,
        storage: Optional[AbstractTraceStorage] = None,
        timeline_builder: Optional[AbstractTimelineBuilder] = None,
        latency_analyzer: Optional[AbstractLatencyAnalyzer] = None,
        search_engine: Optional[AbstractTraceSearchEngine] = None,
    ) -> None:
        self.config = config or TraceConfig.from_env()
        self.storage = storage or DefaultInMemoryTraceStorage(self.config)
        self.timeline_builder = timeline_builder or DefaultTimelineBuilder()
        self.latency_analyzer = latency_analyzer or DefaultLatencyAnalyzer()
        self.search_engine = search_engine or DefaultTraceSearchEngine(self.storage)

        # Active trace span collectors: trace_id -> List[Span]
        self._trace_spans: Dict[str, List[Span]] = {}
        self._total_completed_duration_ms: float = 0.0
        self._total_completed_traces: int = 0
        self._total_spans_recorded: int = 0

    def get_current_span(self) -> Optional[Span]:
        return _CURRENT_SPAN.get()

    def get_current_context(self) -> Optional[TraceContext]:
        return _CURRENT_CONTEXT.get()

    def set_current_context(self, context: TraceContext) -> None:
        _CURRENT_CONTEXT.set(context)

    def start_trace(
        self,
        component: str,
        operation: str,
        context: Optional[TraceContext] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Span:
        if not self.config.enabled:
            return Span.create(component=component, operation=operation, context=context)

        try:
            ctx = context or TraceContext()
            span = Span.create(
                component=component,
                operation=operation,
                context=ctx,
                parent_span_id=None,
                metadata=metadata,
            )

            # Store in active collector
            if ctx.trace_id not in self._trace_spans:
                self._trace_spans[ctx.trace_id] = []
            self._trace_spans[ctx.trace_id].append(span)

            self.storage.store_active_span(span)
            _CURRENT_SPAN.set(span)
            _CURRENT_CONTEXT.set(ctx)

            # Metrics
            try:
                event_metrics.increment("active_traces", 1)
                event_metrics.increment("span_count", 1)
            except Exception:
                pass

            return span
        except Exception as e:
            logger.debug(f"[Tracing] Error starting trace: {e}")
            return Span.create(component=component, operation=operation, context=context)

    def start_span(
        self,
        component: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[TraceContext] = None,
        parent_span: Optional[Span] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Span:
        comp = component or kwargs.pop("component_name", "unknown")
        op = operation or kwargs.pop("operation_name", "unknown")
        meta = metadata if metadata is not None else kwargs.pop("tags", None)

        if not self.config.enabled:
            return Span.create(component=comp, operation=op, context=context)

        try:
            active_parent = parent_span or self.get_current_span()
            parent_ctx = active_parent.context if active_parent else self.get_current_context()

            if parent_ctx:
                child_ctx = parent_ctx.create_child_context(
                    span_id=generate_span_id(),
                    **(context.to_dict() if context else {})
                )
                parent_span_id = active_parent.span_id if active_parent else parent_ctx.span_id
            else:
                child_ctx = context or TraceContext()
                parent_span_id = None

            span = Span.create(
                component=comp,
                operation=op,
                context=child_ctx,
                parent_span_id=parent_span_id,
                metadata=meta,
            )

            if active_parent:
                active_parent.add_child(span)

            trace_id = child_ctx.trace_id
            if trace_id not in self._trace_spans:
                self._trace_spans[trace_id] = []
            self._trace_spans[trace_id].append(span)

            self.storage.store_active_span(span)
            _CURRENT_SPAN.set(span)
            _CURRENT_CONTEXT.set(child_ctx)

            try:
                event_metrics.increment("span_count", 1)
            except Exception:
                pass

            return span
        except Exception as e:
            logger.debug(f"[Tracing] Error starting span: {e}")
            return Span.create(component=comp, operation=op, context=context)

    def finish_span(
        self,
        span: Span,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[Any] = None,
    ) -> Span:
        if not self.config.enabled:
            return span

        try:
            if error is not None:
                span.fail(error=error, metadata=metadata)
            else:
                span.finish(metadata=metadata)

            self.storage.store_active_span(span)
            self._total_spans_recorded += 1

            # Restore parent span if applicable
            current = self.get_current_span()
            if current and current.span_id == span.span_id:
                # Clear or revert context
                _CURRENT_SPAN.set(None)

            return span
        except Exception as e:
            logger.debug(f"[Tracing] Error finishing span: {e}")
            return span

    def finish_trace(
        self,
        root_span: Span,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[Any] = None,
    ) -> Optional[TraceSnapshot]:
        if not self.config.enabled:
            return None

        try:
            self.finish_span(root_span, metadata=metadata, error=error)
            trace_id = root_span.trace_id

            all_spans = self._trace_spans.pop(trace_id, [root_span])
            if root_span not in all_spans:
                all_spans.append(root_span)

            # Build timeline & latency breakdown
            timeline = self.timeline_builder.build_timeline(trace_id, all_spans, root_span)
            latency_breakdown = self.latency_analyzer.analyze_latencies(trace_id, all_spans, timeline)

            # Collect errors and warnings
            errors: List[Dict[str, Any]] = []
            warnings: List[Dict[str, Any]] = []
            for s in all_spans:
                if s.status == SpanStatus.FAILED or s.error:
                    errors.append({"span_id": s.span_id, "component": s.component, "operation": s.operation, "error": s.error})
                if s.metadata.get("warning"):
                    warnings.append({"span_id": s.span_id, "component": s.component, "warning": s.metadata["warning"]})

            snapshot = TraceSnapshot(
                trace_id=trace_id,
                root_span=root_span,
                spans=all_spans,
                span_tree=root_span.to_tree_dict(),
                timeline=timeline,
                latency_breakdown=latency_breakdown,
                critical_path_spans=timeline.critical_path_span_ids,
                component_durations_ms=latency_breakdown.component_durations_ms,
                errors=errors,
                warnings=warnings,
                created_at=datetime.now(timezone.utc),
            )

            # Persist snapshot
            self.storage.finish_trace(trace_id, snapshot)

            # Update aggregate metrics
            self._total_completed_traces += 1
            dur = root_span.duration_ms or 0.0
            self._total_completed_duration_ms += dur

            try:
                event_metrics.decrement("active_traces", 1)
                if root_span.status == SpanStatus.FAILED:
                    event_metrics.increment("failed_traces", 1)
                else:
                    event_metrics.increment("completed_traces", 1)

                avg_dur = int(round(self._total_completed_duration_ms / max(1, self._total_completed_traces)))
                event_metrics.set("average_trace_duration", avg_dur)

                avg_spans = int(round(self._total_spans_recorded / max(1, self._total_completed_traces)))
                event_metrics.set("average_spans_per_trace", avg_spans)

                event_metrics.set("trace_storage_size", self.storage.get_total_traces_count())
                event_metrics.set("critical_path_duration", int(round(timeline.critical_path_duration_ms)))
            except Exception:
                pass

            # Passively notify Execution Intelligence Engine
            try:
                from app.events.intelligence import intelligence_engine
                intelligence_engine.record_completed_trace(snapshot)
            except Exception:
                pass

            return snapshot
        except Exception as e:
            logger.debug(f"[Tracing] Error finalizing trace: {e}")
            return None

    def get_trace(self, trace_id: str) -> Optional[TraceSnapshot]:
        try:
            return self.storage.get_trace(trace_id)
        except Exception as e:
            logger.debug(f"[Tracing] Error fetching trace: {e}")
            return None

    def search_traces(self, query: TraceSearchQuery) -> TraceSearchResult:
        try:
            try:
                event_metrics.increment("trace_search_requests", 1)
            except Exception:
                pass
            return self.search_engine.search(query)
        except Exception as e:
            logger.debug(f"[Tracing] Error searching traces: {e}")
            return TraceSearchResult(total=0, limit=query.limit, offset=query.offset, traces=[])

    # ── Context Managers for Clean Instrumentation ──

    @contextmanager
    def span(
        self,
        component: str,
        operation: str,
        context: Optional[TraceContext] = None,
        parent_span: Optional[Span] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Generator[Span, None, None]:
        """Synchronous context manager for tracing a block of execution."""
        span_obj = self.start_span(
            component=component,
            operation=operation,
            context=context,
            parent_span=parent_span,
            metadata=metadata,
        )
        token = _CURRENT_SPAN.set(span_obj)
        try:
            yield span_obj
        except Exception as exc:
            self.finish_span(span_obj, error=exc)
            raise
        else:
            self.finish_span(span_obj)
        finally:
            _CURRENT_SPAN.reset(token)

    @asynccontextmanager
    async def span_async(
        self,
        component: str,
        operation: str,
        context: Optional[TraceContext] = None,
        parent_span: Optional[Span] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Span, None]:
        """Asynchronous context manager for tracing an async block of execution."""
        span_obj = self.start_span(
            component=component,
            operation=operation,
            context=context,
            parent_span=parent_span,
            metadata=metadata,
        )
        token = _CURRENT_SPAN.set(span_obj)
        try:
            yield span_obj
        except Exception as exc:
            self.finish_span(span_obj, error=exc)
            raise
        else:
            self.finish_span(span_obj)
        finally:
            _CURRENT_SPAN.reset(token)
