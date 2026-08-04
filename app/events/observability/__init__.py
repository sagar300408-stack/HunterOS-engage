"""
HunterOS Engage — Event Observability Package
app/events/observability/__init__.py

Exports the global metrics singleton and timeline/latency utilities.
"""

from app.events.observability.metrics import EventMetrics, event_metrics
from app.events.observability.timeline import (
    TimelineEntry,
    LatencyMetrics,
    build_timeline,
    compute_latencies,
)

__all__ = [
    "event_metrics",
    "EventMetrics",
    "TimelineEntry",
    "LatencyMetrics",
    "build_timeline",
    "compute_latencies",
]
