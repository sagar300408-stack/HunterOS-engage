"""
HunterOS Engage — Distributed Tracing, Execution Observability & Latency Intelligence
app/events/tracing/__init__.py
"""

from app.events.tracing.config import TraceConfig
from app.events.tracing.context import TraceContext, generate_span_id, generate_trace_id
from app.events.tracing.instrumentation import (
    extract_trace_context,
    inject_trace_context,
    trace_span_async,
    trace_span_sync,
)
from app.events.tracing.latency import (
    AbstractLatencyAnalyzer,
    DefaultLatencyAnalyzer,
    LatencyBreakdown,
)
from app.events.tracing.manager import AbstractTraceManager, DefaultTraceManager
from app.events.tracing.search import (
    AbstractTraceSearchEngine,
    DefaultTraceSearchEngine,
    TraceSearchQuery,
    TraceSearchResult,
)
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import Span, SpanStatus
from app.events.tracing.storage import AbstractTraceStorage, DefaultInMemoryTraceStorage
from app.events.tracing.timeline import (
    AbstractTimelineBuilder,
    DefaultTimelineBuilder,
    ExecutionTimeline,
    TimelineSpanEntry,
)
from app.events.tracing.validator import TracingStartupValidator

# Global singleton instance for application-wide distributed tracing
_config = TraceConfig.from_env()
_storage = DefaultInMemoryTraceStorage(_config)
_timeline_builder = DefaultTimelineBuilder()
_latency_analyzer = DefaultLatencyAnalyzer()
_search_engine = DefaultTraceSearchEngine(_storage)

trace_manager: DefaultTraceManager = DefaultTraceManager(
    config=_config,
    storage=_storage,
    timeline_builder=_timeline_builder,
    latency_analyzer=_latency_analyzer,
    search_engine=_search_engine,
)

__all__ = [
    "TraceConfig",
    "TraceContext",
    "generate_trace_id",
    "generate_span_id",
    "Span",
    "SpanStatus",
    "AbstractTraceManager",
    "DefaultTraceManager",
    "AbstractTraceStorage",
    "DefaultInMemoryTraceStorage",
    "AbstractTimelineBuilder",
    "DefaultTimelineBuilder",
    "ExecutionTimeline",
    "TimelineSpanEntry",
    "AbstractLatencyAnalyzer",
    "DefaultLatencyAnalyzer",
    "LatencyBreakdown",
    "AbstractTraceSearchEngine",
    "DefaultTraceSearchEngine",
    "TraceSearchQuery",
    "TraceSearchResult",
    "TraceSnapshot",
    "TracingStartupValidator",
    "inject_trace_context",
    "extract_trace_context",
    "trace_span_sync",
    "trace_span_async",
    "trace_manager",
]
