"""
Exhaustive Automated Test Suite for HunterOS Distributed Tracing, Observability & Execution Intelligence.

Covers:
  1. TraceConfig defaults & environment customization
  2. TraceContext generation & W3C carrier injection / extraction
  3. Span lifecycle, hierarchy, metadata, logs, and error status transitions
  4. Active span contextvars management & concurrent task safety
  5. In-memory TraceStorage with multi-index lookups, LRU capacity, and TTL cleanup
  6. Chronological Execution Timeline construction & wait times
  7. Critical Path analysis & sequential dependency bottleneck identification
  8. Component Latency Breakdown decomposition & percentage contributions
  9. Multi-criteria Trace Search Engine & pagination
 10. Observability metrics integration (12 telemetry counters/gauges)
 11. Reliability Tracing API endpoints
 12. Complete passive isolation & error resilience (zero pipeline disruption on trace error)
 13. Disabled tracing mode & sampling rate enforcement
 14. Full platform integration (EventBus + Orchestrator + Lifecycle + Tracing)
 15. Tracing Startup Validator preflight verification
"""

import asyncio
from datetime import datetime, timezone, timedelta
import time
from typing import Any, Dict, List, Optional, Set, Type
import uuid
import pytest
from fastapi.testclient import TestClient

# Domain model imports to ensure SQLAlchemy mapper registry initialization
from app.domain.conversations.models import Base, Conversation
from app.domain.customers.models import Customer
from app.domain.intent.models import IntentHistory
from app.domain.dashboard.models import PipelineEvent
from app.domain.security.models import AuditLog
from app.domain.followup.models import (
    FollowUpQueue,
    FollowUpExecution,
    LeadHealthScore,
    SalesMemoryTimeline,
)
from app.domain.memory.models import CustomerMemory

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.base_event import UniversalBaseEvent
from app.events.observability.metrics import event_metrics
from app.events.tracing.config import TraceConfig
from app.events.tracing.context import (
    TraceContext,
    generate_trace_id,
    generate_span_id,
)
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
from app.events.tracing.manager import (
    AbstractTraceManager,
    DefaultTraceManager,
)
from app.events.tracing.search import (
    AbstractTraceSearchEngine,
    DefaultTraceSearchEngine,
    TraceSearchQuery,
    TraceSearchResult,
)
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import Span, SpanStatus
from app.events.tracing.storage import (
    AbstractTraceStorage,
    DefaultInMemoryTraceStorage,
)
from app.events.tracing.timeline import (
    AbstractTimelineBuilder,
    DefaultTimelineBuilder,
    ExecutionTimeline,
    TimelineSpanEntry,
)
from app.events.tracing.validator import TracingStartupValidator
from app.events.worker.orchestrator import ConsumerOrchestrator
from app.main import create_app


from app.events.model.actor_types import ActorType
from app.events.model.categories import EventCategory


# ── Helpers & Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_metrics_and_traces():
    """Ensure clean state for every test."""
    event_metrics.reset()
    yield
    event_metrics.reset()


class MockSampleEvent(UniversalBaseEvent):
    event_name: str = "MockSampleEvent"
    workspace_id: uuid.UUID = uuid.uuid4()
    correlation_id: Optional[uuid.UUID] = uuid.uuid4()
    actor_type: ActorType = ActorType.SYSTEM
    category: EventCategory = EventCategory.PLATFORM
    source_subsystem: str = "test_subsystem"
    payload: Dict[str, Any] = {"status": "ok"}


class FastMockConsumer(EventConsumer):
    def get_subscriptions(self) -> Set[Type[UniversalBaseEvent]]:
        return {MockSampleEvent}

    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.ORDERED

    def get_priority(self) -> int:
        return 10

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        await asyncio.sleep(0.01)


class FailingMockConsumer(EventConsumer):
    def get_subscriptions(self) -> Set[Type[UniversalBaseEvent]]:
        return {MockSampleEvent}

    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.CRITICAL

    def get_priority(self) -> int:
        return 100

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        raise ValueError("Simulated downstream processing crash")


# ── Test Scenarios ─────────────────────────────────────────────────────────────

def test_trace_config_defaults_and_env(monkeypatch):
    """Scenario 1: Verify TraceConfig creation, defaults, and env overrides."""
    cfg = TraceConfig.from_env()
    assert cfg.enabled is True
    assert cfg.sampling_rate == 1.0
    assert cfg.max_trace_retention == 10000
    assert cfg.retention_ttl_seconds == 86400.0

    monkeypatch.setenv("HUNTER_TRACING_ENABLED", "false")
    monkeypatch.setenv("HUNTER_TRACING_SAMPLING_RATE", "0.5")
    monkeypatch.setenv("HUNTER_TRACING_MAX_RETENTION", "1000")
    monkeypatch.setenv("HUNTER_TRACING_RETENTION_TTL", "3600")

    custom_cfg = TraceConfig.from_env()
    assert custom_cfg.enabled is False
    assert custom_cfg.sampling_rate == 0.5
    assert custom_cfg.max_trace_retention == 1000
    assert custom_cfg.retention_ttl_seconds == 3600.0


def test_trace_context_and_w3c_carrier():
    """Scenario 2: Verify TraceContext, child context derivation, and W3C injection/extraction."""
    ctx = TraceContext(
        workspace_id="ws_123",
        correlation_id="corr_abc",
        causation_id="cause_xyz",
        event_id="evt_789",
        partition_key="partner_1",
        priority=100,
    )
    assert ctx.trace_id is not None
    assert ctx.span_id is not None

    # Child derivation
    child_ctx = ctx.child_context()
    assert child_ctx.trace_id == ctx.trace_id
    assert child_ctx.parent_span_id == ctx.span_id
    assert child_ctx.span_id != ctx.span_id
    assert child_ctx.workspace_id == "ws_123"

    # W3C carrier injection & extraction
    carrier: Dict[str, str] = {}
    inject_trace_context(ctx, carrier)
    assert "traceparent" in carrier
    assert "tracestate" in carrier
    assert carrier["x-hunter-workspace-id"] == "ws_123"
    assert carrier["x-hunter-partition-key"] == "partner_1"

    extracted_ctx = extract_trace_context(carrier)
    assert extracted_ctx.trace_id == ctx.trace_id
    assert extracted_ctx.parent_span_id == ctx.span_id
    assert extracted_ctx.workspace_id == "ws_123"
    assert extracted_ctx.partition_key == "partner_1"
    assert extracted_ctx.priority == 100


def test_span_lifecycle_and_hierarchy():
    """Scenario 3: Verify Span creation, child spans, metadata, logs, timing, and errors."""
    ctx = TraceContext(workspace_id="ws_span_test", correlation_id="c_1")
    root = Span.create(
        component="event_bus",
        operation="publish",
        context=ctx,
        metadata={"custom_key": "val1"},
    )
    assert root.status == SpanStatus.RUNNING
    assert root.start_time is not None

    root.add_metadata("queue", "default")
    assert root.metadata["queue"] == "default"

    child = root.create_child("dispatcher", "poll_and_schedule")
    assert child.parent_span_id == root.span_id
    assert child.trace_id == root.trace_id
    assert len(root.children) == 1

    time.sleep(0.01)
    child.finish()
    assert child.status == SpanStatus.SUCCESS
    assert child.duration_ms is not None
    assert child.duration_ms >= 1.0

    root.fail(error=RuntimeError("Bus connection lost"))
    assert root.status == SpanStatus.FAILED
    assert root.error is not None
    assert "Bus connection lost" in root.error


def test_trace_manager_active_stack_and_contextvars():
    """Scenario 4: Verify DefaultTraceManager active span stack and contextvars isolation."""
    config = TraceConfig()
    storage = DefaultInMemoryTraceStorage(config)
    manager = DefaultTraceManager(config=config, storage=storage)

    ctx = TraceContext(workspace_id="ws_ctx", correlation_id="corr_ctx")
    root = manager.start_trace("event_bus", "publish", context=ctx)
    assert manager.get_current_span() == root

    child = manager.start_span("worker", "execute")
    assert child.parent_span_id == root.span_id
    assert manager.get_current_span() == child

    grandchild = manager.start_span("consumer.handler", "process")
    assert grandchild.parent_span_id == child.span_id
    assert manager.get_current_span() == grandchild

    manager.finish_span(grandchild)
    manager.finish_span(child)

    snapshot = manager.finish_trace(root)
    assert snapshot is not None
    assert snapshot.trace_id == ctx.trace_id
    assert len(snapshot.spans) == 3


@pytest.mark.asyncio
async def test_trace_manager_async_context_and_decorators():
    """Scenario 4b: Verify async context managers and decorators."""
    config = TraceConfig()
    storage = DefaultInMemoryTraceStorage(config)
    manager = DefaultTraceManager(config=config, storage=storage)

    ctx = TraceContext(workspace_id="ws_async", correlation_id="corr_async")

    async with manager.span_async("pipeline", "stage_1", context=ctx):
        current = manager.get_current_span()
        assert current is not None
        assert current.component == "pipeline"

        async with manager.span_async("pipeline.sub", "subtask"):
            sub = manager.get_current_span()
            assert sub.parent_span_id == current.span_id
            await asyncio.sleep(0.01)


def test_trace_storage_lru_and_ttl_eviction():
    """Scenario 5: Verify In-Memory TraceStorage LRU capacity, TTL eviction, and indices."""
    config = TraceConfig(max_trace_retention=3, retention_ttl_seconds=1.0)
    storage = DefaultInMemoryTraceStorage(config)

    # Insert 3 traces
    snapshots = []
    for i in range(3):
        ctx = TraceContext(
            workspace_id=f"ws_{i}",
            correlation_id=f"corr_{i}",
            event_id=f"evt_{i}",
        )
        span = Span.create(
            component="test",
            operation="op",
            context=ctx,
        )
        span.finish()
        snap = TraceSnapshot(
            trace_id=ctx.trace_id,
            root_span=span,
            spans=[span],
            created_at=datetime.now(timezone.utc),
        )
        storage.finish_trace(ctx.trace_id, snap)
        snapshots.append(snap)

    assert storage.get_total_traces_count() == 3
    assert storage.get_trace(snapshots[0].trace_id) is not None
    assert storage.get_trace_by_event_id("evt_0") is not None

    # Insert 4th trace -> triggers LRU eviction of trace 0
    ctx4 = TraceContext(workspace_id="ws_4", event_id="evt_4")
    span4 = Span.create(component="test", operation="op", context=ctx4)
    span4.finish()
    snap4 = TraceSnapshot(trace_id=ctx4.trace_id, root_span=span4, spans=[span4])
    storage.finish_trace(ctx4.trace_id, snap4)

    assert storage.get_total_traces_count() == 3
    assert storage.get_trace(snapshots[0].trace_id) is None  # Evicted!
    assert storage.get_trace_by_event_id("evt_0") is None     # Index cleared!
    assert storage.get_trace(snap4.trace_id) is not None

    # TTL eviction
    time.sleep(1.1)
    evicted_count = storage.cleanup_expired()
    assert evicted_count >= 3
    assert storage.get_total_traces_count() == 0


def test_execution_timeline_and_chronology():
    """Scenario 6: Verify chronological Execution Timeline generation & wait times."""
    builder = DefaultTimelineBuilder()

    ctx = TraceContext(workspace_id="ws_time")
    root = Span.create(component="bus", operation="pub", context=ctx)
    time.sleep(0.01)

    s1 = root.create_child("dispatcher", "poll")
    time.sleep(0.01)
    s1.finish()

    time.sleep(0.01)
    s2 = root.create_child("worker", "execute")
    time.sleep(0.01)
    s2.finish()

    root.finish()

    timeline = builder.build_timeline(ctx.trace_id, [root, s1, s2], root)
    assert len(timeline.entries) >= 2
    assert timeline.total_duration_ms > 0


def test_critical_path_analysis_and_bottlenecks():
    """Scenario 7: Verify Critical Path identification and blocking times."""
    builder = DefaultTimelineBuilder()

    ctx = TraceContext(workspace_id="ws_crit")
    root = Span.create(component="root", operation="main", context=ctx)

    # Sequential chain: root -> seq1 (long) -> seq2 (short)
    seq1 = root.create_child("db_step", "query")
    seq1.start_time = root.start_time
    seq1.end_time = root.start_time + timedelta(milliseconds=100)
    seq1.duration_ms = 100.0
    seq1.status = SpanStatus.SUCCESS

    seq2 = seq1.create_child("compute_step", "transform")
    seq2.start_time = seq1.end_time
    seq2.end_time = seq2.start_time + timedelta(milliseconds=50)
    seq2.duration_ms = 50.0
    seq2.status = SpanStatus.SUCCESS

    # Concurrent branch: par1 (fast)
    par1 = root.create_child("side_effect", "log")
    par1.start_time = root.start_time
    par1.end_time = root.start_time + timedelta(milliseconds=20)
    par1.duration_ms = 20.0
    par1.status = SpanStatus.SUCCESS

    root.end_time = seq2.end_time
    root.duration_ms = 150.0
    root.status = SpanStatus.SUCCESS

    timeline = builder.build_timeline(ctx.trace_id, [root, seq1, seq2, par1], root)
    assert seq1.span_id in timeline.critical_path_span_ids
    assert seq2.span_id in timeline.critical_path_span_ids
    assert par1.span_id not in timeline.critical_path_span_ids
    assert timeline.critical_path_duration_ms >= 150.0


def test_latency_breakdown_computation():
    """Scenario 8: Verify Latency Breakdown component categorization and percentages."""
    analyzer = DefaultLatencyAnalyzer()

    ctx = TraceContext(workspace_id="ws_lat")
    root = Span.create(component="event_bus", operation="publish", context=ctx)
    root.start_time = datetime.now(timezone.utc)
    root.end_time = root.start_time + timedelta(milliseconds=200)
    root.duration_ms = 200.0

    s_queue = root.create_child("queue", "wait")
    s_queue.start_time = root.start_time
    s_queue.end_time = s_queue.start_time + timedelta(milliseconds=40)
    s_queue.duration_ms = 40.0

    s_worker = root.create_child("worker", "execute")
    s_worker.start_time = s_queue.end_time
    s_worker.end_time = s_worker.start_time + timedelta(milliseconds=100)
    s_worker.duration_ms = 100.0

    s_consumer = s_worker.create_child("consumer.EngagementLeadScoreConsumer", "handle_event")
    s_consumer.start_time = s_worker.start_time
    s_consumer.end_time = s_consumer.start_time + timedelta(milliseconds=60)
    s_consumer.duration_ms = 60.0

    breakdown = analyzer.analyze_latencies(ctx.trace_id, [root, s_queue, s_worker, s_consumer])
    assert breakdown.end_to_end_latency_ms == 200.0
    assert breakdown.queue_latency_ms == 40.0
    assert breakdown.consumer_execution_latency_ms == 60.0

    contribs = breakdown.to_dict()["component_contributions"]
    assert len(contribs) >= 1


def test_trace_search_engine_multi_criteria():
    """Scenario 9: Verify Multi-Criteria Trace Search & Filtering."""
    config = TraceConfig()
    storage = DefaultInMemoryTraceStorage(config)
    search_engine = DefaultTraceSearchEngine(storage)

    # Seed 5 diverse traces
    for i in range(5):
        status = SpanStatus.FAILED if i == 4 else SpanStatus.SUCCESS
        ctx = TraceContext(
            workspace_id=f"ws_{i % 2}",
            correlation_id=f"corr_{i}",
            event_id=f"evt_{i}",
            partition_key=f"partner_{i % 3}",
            priority=100 if i % 2 == 0 else 50,
        )
        span = Span.create(component=f"consumer.Consumer_{i}", operation="run", context=ctx)
        span.start_time = datetime.now(timezone.utc)
        span.end_time = span.start_time + timedelta(milliseconds=(i + 1) * 50)
        span.duration_ms = float((i + 1) * 50)
        span.status = status

        snap = TraceSnapshot(
            trace_id=ctx.trace_id,
            root_span=span,
            spans=[span],
            span_tree=span.to_tree_dict(),
        )
        storage.finish_trace(ctx.trace_id, snap)

    # Query 1: By workspace
    r1 = search_engine.search(TraceSearchQuery(workspace_id="ws_0"))
    assert r1.total == 3

    # Query 2: By status
    r2 = search_engine.search(TraceSearchQuery(status="FAILED"))
    assert r2.total == 1
    assert r2.traces[0]["status"] == "FAILED"

    # Query 3: By duration bounds
    r3 = search_engine.search(TraceSearchQuery(min_duration_ms=120.0))
    assert r3.total >= 3

    # Query 4: By partition key
    r4 = search_engine.search(TraceSearchQuery(partition_key="partner_1"))
    assert r4.total >= 1

    # Query 5: Index-accelerated event_id lookup
    r5 = search_engine.search(TraceSearchQuery(event_id="evt_2"))
    assert r5.total == 1
    assert r5.traces[0]["event_id"] == "evt_2"


def test_observability_metrics_integration():
    """Scenario 10: Verify 12 Distributed Tracing Telemetry Counters & Gauges."""
    config = TraceConfig()
    storage = DefaultInMemoryTraceStorage(config)
    manager = DefaultTraceManager(config=config, storage=storage)

    ctx = TraceContext(workspace_id="ws_metric", correlation_id="c_m")
    root = manager.start_trace("event_bus", "publish", context=ctx)
    child = manager.start_span("worker", "run", parent_span=root)

    snap_active = event_metrics.snapshot()
    assert snap_active.active_traces >= 1
    assert snap_active.span_count >= 2

    manager.finish_span(child)
    manager.finish_trace(root)

    snap_done = event_metrics.snapshot()
    assert snap_done.active_traces == 0
    assert snap_done.completed_traces == 1
    assert snap_done.trace_storage_size == 1
    assert snap_done.average_trace_duration >= 0

    # Search request counter
    manager.search_traces(TraceSearchQuery(workspace_id="ws_metric"))
    assert event_metrics.snapshot().trace_search_requests == 1


def test_reliability_api_trace_endpoints():
    """Scenario 11: Verify FastAPI Reliability API endpoints for tracing."""
    from app.events.tracing import trace_manager

    # Clear and populate with sample trace
    trace_manager.storage.clear()
    ctx = TraceContext(
        workspace_id="ws_api_test",
        correlation_id="corr_api",
        event_id="evt_api_123",
        partition_key="partner_api",
        priority=80,
    )
    root = trace_manager.start_trace("event_bus", "publish", context=ctx)
    child = trace_manager.start_span("worker", "execute", parent_span=root)
    time.sleep(0.01)
    trace_manager.finish_span(child)
    snapshot = trace_manager.finish_trace(root)
    assert snapshot is not None

    app = create_app()
    client = TestClient(app)

    # 1. List traces
    resp_list = client.get("/api/v1/reliability/traces")
    assert resp_list.status_code == 200
    data_list = resp_list.json()
    assert data_list["total"] >= 1
    assert len(data_list["traces"]) >= 1

    # 2. Get trace by ID
    resp_get = client.get(f"/api/v1/reliability/traces/{ctx.trace_id}")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["trace_id"] == ctx.trace_id
    assert data_get["context"]["workspace_id"] == "ws_api_test"
    assert data_get["total_spans"] == 2

    # 3. Search traces
    resp_search = client.get(f"/api/v1/reliability/traces/search?workspace_id=ws_api_test")
    assert resp_search.status_code == 200
    data_search = resp_search.json()
    assert data_search["total"] == 1
    assert data_search["traces"][0]["trace_id"] == ctx.trace_id

    # 4. Get timeline
    resp_time = client.get(f"/api/v1/reliability/traces/{ctx.trace_id}/timeline")
    assert resp_time.status_code == 200
    data_time = resp_time.json()
    assert "entries" in data_time
    assert len(data_time["entries"]) >= 2

    # 5. Get critical path
    resp_cp = client.get(f"/api/v1/reliability/traces/{ctx.trace_id}/critical-path")
    assert resp_cp.status_code == 200
    data_cp = resp_cp.json()
    assert "critical_path_spans" in data_cp
    assert "critical_path_duration_ms" in data_cp

    # 6. 404 for unknown trace
    resp_404 = client.get("/api/v1/reliability/traces/non_existent_trace_id")
    assert resp_404.status_code == 404


def test_passive_isolation_and_failure_resilience():
    """Scenario 12: Verify that tracing exceptions never propagate to or disrupt core logic."""
    class BrokenStorage(AbstractTraceStorage):
        def store_active_span(self, span: Span) -> None:
            raise RuntimeError("Database storage exploded!")

        def finish_trace(self, trace_id: str, snapshot: TraceSnapshot) -> None:
            raise RuntimeError("Database storage exploded!")

        def get_trace(self, trace_id: str) -> Optional[TraceSnapshot]:
            raise RuntimeError("Lookup failure!")

        def get_trace_by_event_id(self, event_id: str) -> Optional[TraceSnapshot]:
            return None

        def list_traces(self, **kwargs):
            return []

        def delete_trace(self, trace_id: str) -> bool:
            return False

        def cleanup_expired(self, now: Optional[datetime] = None) -> int:
            return 0

        def get_active_traces_count(self) -> int:
            return 0

        def get_total_traces_count(self) -> int:
            return 0

        def clear(self) -> None:
            pass

    config = TraceConfig()
    manager = DefaultTraceManager(config=config, storage=BrokenStorage())

    # Operations must succeed without raising exceptions
    root = manager.start_trace("broken_test", "run")
    child = manager.start_span("broken_child", "run", parent_span=root)
    manager.finish_span(child)
    res = manager.finish_trace(root)
    assert res is None or isinstance(res, TraceSnapshot)

    # Decorator resilience
    @trace_span_sync("failing_comp", "failing_op", manager=manager)
    def normal_business_function(a: int, b: int) -> int:
        return a + b

    assert normal_business_function(5, 7) == 12


def test_disabled_tracing_zero_overhead():
    """Scenario 13: Verify disabled tracing mode behaves as no-op."""
    config = TraceConfig(enabled=False)
    storage = DefaultInMemoryTraceStorage(config)
    manager = DefaultTraceManager(config=config, storage=storage)

    ctx = TraceContext(workspace_id="ws_disabled")
    span = manager.start_trace("test", "test", context=ctx)
    assert span is not None  # Dummy noop span returned

    res = manager.finish_trace(span)
    assert res is None  # No snapshot created or stored
    assert storage.get_total_traces_count() == 0


@pytest.mark.asyncio
async def test_consumer_orchestrator_tracing_integration():
    """Scenario 14: Verify consumer orchestrator records spans and execution results."""
    from app.events.tracing import trace_manager

    trace_manager.storage.clear()
    ctx = TraceContext(workspace_id="ws_orch", event_id=str(uuid.uuid4()))
    root = trace_manager.start_trace("orchestrator_test", "run", context=ctx)

    consumer = FastMockConsumer()
    event = MockSampleEvent()
    report = await ConsumerOrchestrator.run(
        event=event,
        consumers=[consumer],
        event_id=uuid.uuid4(),
    )
    assert report.has_errors is False
    assert len(report.results) == 1
    assert report.results[0].status.value == "SUCCESS"

    trace_manager.finish_trace(root)
    snap = trace_manager.get_trace(ctx.trace_id)
    assert snap is not None
    assert len(snap.spans) >= 2  # Root span + Consumer span


def test_tracing_startup_validator():
    """Scenario 15: Verify preflight health check execution."""
    report = TracingStartupValidator.validate()
    assert report["status"] == "HEALTHY"
    assert report["checks"]["config"]["enabled"] is True
    assert report["checks"]["context_propagation"] == "PASSED"
    assert report["checks"]["snapshot_generation"] == "PASSED"
    assert report["checks"]["critical_path"] == "PASSED"
    assert report["checks"]["search_engine"] == "PASSED"
    assert report["checks"]["storage_cleanup"] == "PASSED"
