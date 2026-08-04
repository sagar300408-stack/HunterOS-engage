"""
HunterOS Engage — Event Observability & Distributed Tracing Tests
tests/events/test_event_observability.py

Validates:
1. EventMetrics singleton (counters, gauges, snapshots, reset).
2. ConsumerResult timing model (started_at, finished_at, duration_ms, to_dict).
3. Timeline builder (ordered lifecycle transitions, timestamp mapping).
4. Latency calculation (Persist->Queue, Queue->Processing, Processing->Completion,
   End-to-End, Per-Consumer, Per-Stage).
5. Trace response reconstruction (build_trace_response).
6. LifecycleManager history tracking (retry_history, replay_history).
7. Worker task execution & span persistence in _dispatch_async.
8. REST API endpoints (GET /reliability/health and GET /reliability/trace/{event_id}).
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4, UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.domain.conversations.models import Base
from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.actor_types import ActorType
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.lifecycle import EventLifecycleState
from app.events.lifecycle.manager import LifecycleManager
from app.events.observability.metrics import EventMetrics, event_metrics
from app.events.observability.timeline import (
    TimelineEntry,
    LatencyMetrics,
    build_timeline,
    compute_latencies,
    build_trace_response,
)
from app.events.registry.registry import registry
from app.events.store.models import EventRecord
from app.events.store.repository import EventStoreRepository
from app.events.store.service import EventStoreService
from app.events.worker.orchestrator import ConsumerOrchestrator, ConsumerResult, ConsumerStatus
from app.events.worker.planner import PlanBuilder
from app.events.worker.tasks import _dispatch_async
from app.main import create_app


# ── Test Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset the metrics singleton and isolate registry state before every test."""
    event_metrics.reset()
    saved_subscriptions = {k: list(v) for k, v in registry._subscriptions.items()}
    yield
    event_metrics.reset()
    registry._subscriptions.clear()
    registry._subscriptions.update(saved_subscriptions)


@pytest_asyncio.fixture
async def async_session():
    """In-memory SQLite async database session for isolated database testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(EventRecord.__table__.create)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session

    await engine.dispose()


# ── 1. EventMetrics Tests ──────────────────────────────────────────────────────

def test_metrics_counter_operations():
    """Validates increment, decrement, set, and snapshot capabilities."""
    m = EventMetrics()

    m.increment("processed", 5)
    m.increment("failed", 2)
    m.increment("active_processing", 3)
    m.decrement("active_processing", 1)
    m.increment("dispatcher_cycles", 10)
    m.increment("retried", 4)
    m.increment("dead_lettered", 1)
    m.increment("replayed", 2)

    snap = m.snapshot()
    assert snap.events_processed == 5
    assert snap.events_failed == 2
    assert snap.events_active_processing == 2
    assert snap.dispatcher_cycles == 10
    assert snap.events_retried == 4
    assert snap.events_dead_lettered == 1
    assert snap.events_replayed == 2

    d = snap.to_dict()
    assert d["events_processed"] == 5
    assert d["events_active_processing"] == 2

    # Reset clears all
    m.reset()
    snap_after = m.snapshot()
    assert snap_after.events_processed == 0
    assert snap_after.events_active_processing == 0


def test_metrics_decrement_floor_zero():
    """Decrementing below zero must floor at 0."""
    m = EventMetrics()
    m.decrement("active_processing", 10)
    assert m.snapshot().events_active_processing == 0


def test_metrics_invalid_key():
    """Accessing an unknown metric key raises KeyError."""
    m = EventMetrics()
    with pytest.raises(KeyError):
        m.increment("invalid_metric_key")


# ── 2. ConsumerResult Timing Model ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consumer_result_timestamps():
    """Consumer execution captures started_at, finished_at, and duration_ms."""
    class FastConsumer(EventConsumer):
        def get_subscriptions(self):
            return [UniversalBaseEvent]

        def get_execution_policy(self) -> ExecutionPolicy:
            return ExecutionPolicy.ORDERED

        def get_priority(self) -> int:
            return 10

        async def handle_event(self, event: UniversalBaseEvent) -> None:
            await asyncio.sleep(0.01)

    c = FastConsumer()
    event = UniversalBaseEvent(
        workspace_id=uuid4(),
        actor_type=ActorType.SYSTEM,
        source_subsystem="test",
        category=EventCategory.PLATFORM,
        event_name="TestTimingEvent",
    )

    res = await ConsumerOrchestrator._run_one(event, c, event_id=uuid4(), stage_index=0)
    assert res.status == ConsumerStatus.SUCCESS
    assert res.started_at is not None
    assert res.finished_at is not None
    assert res.finished_at >= res.started_at
    assert res.duration_ms >= 5
    assert res.stage_index == 0

    d = res.to_dict()
    assert d["consumer"] == "FastConsumer"
    assert d["started_at"] is not None
    assert d["finished_at"] is not None
    assert d["status"] == "SUCCESS"


# ── 3. Timeline Builder ────────────────────────────────────────────────────────

def test_timeline_builder_complete_lifecycle():
    """build_timeline extracts ordered chronological milestones from EventRecord."""
    t0 = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(milliseconds=50)
    t2 = t1 + timedelta(milliseconds=30)
    t3 = t2 + timedelta(milliseconds=120)

    record = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        occurred_at=t0,
        queued_at=t1,
        processing_started_at=t2,
        completed_at=t3,
        lifecycle_state=EventLifecycleState.COMPLETED.value,
    )

    timeline = build_timeline(record)
    assert len(timeline) == 4
    assert [e.state for e in timeline] == ["PERSISTED", "QUEUED", "PROCESSING", "COMPLETED"]
    assert timeline[0].timestamp == t0
    assert timeline[1].timestamp == t1
    assert timeline[2].timestamp == t2
    assert timeline[3].timestamp == t3


def test_timeline_builder_partial_lifecycle():
    """build_timeline handles events still in flight gracefully."""
    t0 = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(milliseconds=50)

    record = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        occurred_at=t0,
        queued_at=t1,
        processing_started_at=None,
        completed_at=None,
        lifecycle_state=EventLifecycleState.QUEUED.value,
    )

    timeline = build_timeline(record)
    assert len(timeline) == 2
    assert [e.state for e in timeline] == ["PERSISTED", "QUEUED"]


# ── 4. Latency Calculations ────────────────────────────────────────────────────

def test_compute_latencies():
    """compute_latencies calculates intervals and consumer/stage breakdowns."""
    t0 = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(milliseconds=100)
    t2 = t1 + timedelta(milliseconds=50)
    t3 = t2 + timedelta(milliseconds=250)

    record = EventRecord(
        event_id=uuid4(),
        workspace_id=uuid4(),
        occurred_at=t0,
        queued_at=t1,
        processing_started_at=t2,
        completed_at=t3,
        lifecycle_state=EventLifecycleState.COMPLETED.value,
    )

    spans = [
        {"consumer": "AuditConsumer", "stage": 0, "duration_ms": 40.0},
        {"consumer": "NotificationConsumer", "stage": 0, "duration_ms": 60.0},
        {"consumer": "AnalyticsConsumer", "stage": 1, "duration_ms": 150.0},
    ]

    lat = compute_latencies(record, spans)
    assert lat.persist_to_queue_ms == pytest.approx(100.0)
    assert lat.queue_to_processing_ms == pytest.approx(50.0)
    assert lat.processing_to_completion_ms == pytest.approx(250.0)
    assert lat.end_to_end_ms == pytest.approx(400.0)
    assert lat.per_consumer_ms["AuditConsumer"] == 40.0
    assert lat.per_consumer_ms["AnalyticsConsumer"] == 150.0
    assert lat.per_stage_ms[0] == 100.0  # 40 + 60
    assert lat.per_stage_ms[1] == 150.0


# ── 5. Trace Response Builder ──────────────────────────────────────────────────

def test_build_trace_response():
    """build_trace_response creates complete response structure with metadata."""
    e_id = uuid4()
    w_id = uuid4()
    c_id = uuid4()
    t0 = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(milliseconds=30)
    t2 = t1 + timedelta(milliseconds=20)
    t3 = t2 + timedelta(milliseconds=80)

    record = EventRecord(
        event_id=e_id,
        event_name="CustomerOnboardedEvent",
        workspace_id=w_id,
        correlation_id=c_id,
        trace_id=f"trace-{e_id}",
        schema_version=1,
        occurred_at=t0,
        queued_at=t1,
        processing_started_at=t2,
        completed_at=t3,
        lifecycle_state=EventLifecycleState.COMPLETED.value,
        retry_count=0,
        metadata_payload={
            "consumer_spans": [
                {"consumer": "WelcomeEmailConsumer", "stage": 0, "duration_ms": 75.0, "status": "SUCCESS"}
            ],
            "retry_history": [],
            "replay_history": [],
        },
    )

    trace = build_trace_response(record)
    assert trace["event_id"] == str(e_id)
    assert trace["event_name"] == "CustomerOnboardedEvent"
    assert trace["workspace_id"] == str(w_id)
    assert trace["trace_id"] == f"trace-{e_id}"
    assert trace["correlation_id"] == str(c_id)
    assert trace["current_state"] == "COMPLETED"
    assert len(trace["timeline"]) == 4
    assert len(trace["consumer_spans"]) == 1
    assert trace["latencies"]["end_to_end_ms"] == pytest.approx(130.0)


# ── 6. LifecycleManager History & Trace Logging ────────────────────────────────

@pytest.mark.asyncio
async def test_lifecycle_retry_and_replay_history(async_session: AsyncSession):
    """LifecycleManager populates retry_history and replay_history in metadata."""
    e_id = uuid4()
    w_id = uuid4()

    record = EventRecord(
        event_id=e_id,
        event_name="PaymentProcessedEvent",
        workspace_id=w_id,
        actor_type="SYSTEM",
        source_subsystem="billing",
        category="TRANSACTION",
        payload={"amount": 100},
        metadata_payload={},
        occurred_at=datetime.now(timezone.utc),
        lifecycle_state=EventLifecycleState.PERSISTED.value,
    )
    async_session.add(record)
    await async_session.commit()

    # Transition PERSISTED -> QUEUED -> PROCESSING
    await LifecycleManager.queue(async_session, e_id)
    await LifecycleManager.processing(async_session, e_id)
    await async_session.commit()

    # Retry transition
    next_retry = datetime.now(timezone.utc) + timedelta(seconds=10)
    await LifecycleManager.retry(async_session, e_id, next_retry_at=next_retry, error_detail="Gateway Timeout")
    await async_session.commit()

    rec = await async_session.get(EventRecord, e_id)
    assert rec.retry_count == 1
    assert "retry_history" in rec.metadata_payload
    assert len(rec.metadata_payload["retry_history"]) == 1
    assert rec.metadata_payload["retry_history"][0]["error_detail"] == "Gateway Timeout"

    # Dead Letter
    await LifecycleManager.requeue(async_session, e_id)
    await LifecycleManager.processing(async_session, e_id)
    await LifecycleManager.dead_letter(async_session, e_id, error_detail="Max retries reached")
    await async_session.commit()

    rec = await async_session.get(EventRecord, e_id)
    assert rec.lifecycle_state == EventLifecycleState.DEAD_LETTER.value

    # Replay
    await LifecycleManager.replay(async_session, e_id)
    await async_session.commit()

    rec = await async_session.get(EventRecord, e_id)
    assert rec.lifecycle_state == EventLifecycleState.REPLAYED.value
    assert "replay_history" in rec.metadata_payload
    assert len(rec.metadata_payload["replay_history"]) == 1
    assert rec.metadata_payload["replay_history"][0]["from_state"] == "DEAD_LETTER"
    assert event_metrics.snapshot().events_replayed == 1


# ── 7. Worker Task Dispatch & Span Recording ──────────────────────────────────

class ObservabilityTestEvent(UniversalBaseEvent):
    event_name: str = "ObservabilityTestEvent"
    category: EventCategory = EventCategory.PLATFORM
    source_subsystem: str = "test"
    actor_type: ActorType = ActorType.SYSTEM


class SuccessfulObserverConsumer(EventConsumer):
    def get_subscriptions(self):
        return [ObservabilityTestEvent]

    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.ORDERED

    def get_priority(self) -> int:
        return 100

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_worker_dispatch_records_spans_and_metrics(async_session: AsyncSession, monkeypatch):
    """_dispatch_async executes consumers, records spans, updates metrics, and marks COMPLETED."""
    registry._subscriptions.clear()
    registry.register(ObservabilityTestEvent, SuccessfulObserverConsumer)

    e_id = uuid4()
    w_id = uuid4()

    record = EventRecord(
        event_id=e_id,
        event_name="ObservabilityTestEvent",
        workspace_id=w_id,
        actor_type="system",
        source_subsystem="test",
        category="PLATFORM",
        payload={
            "event_id": str(e_id),
            "workspace_id": str(w_id),
            "event_name": "ObservabilityTestEvent",
            "category": "PLATFORM",
            "actor_type": "system",
            "source_subsystem": "test",
            "schema_version": 1,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
        metadata_payload={},
        occurred_at=datetime.now(timezone.utc),
        queued_at=datetime.now(timezone.utc),
        lifecycle_state=EventLifecycleState.QUEUED.value,
    )
    async_session.add(record)
    await async_session.commit()

    # Monkeypatch get_session to return our async_session
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_session():
        yield async_session

    monkeypatch.setattr("app.events.worker.tasks.get_session", mock_get_session)

    await _dispatch_async(e_id, max_retries=3)

    rec = await async_session.get(EventRecord, e_id)
    assert rec.lifecycle_state == EventLifecycleState.COMPLETED.value
    assert "consumer_spans" in rec.metadata_payload
    spans = rec.metadata_payload["consumer_spans"]
    assert len(spans) == 1
    assert spans[0]["consumer"] == "SuccessfulObserverConsumer"
    assert spans[0]["status"] == "SUCCESS"
    assert spans[0]["duration_ms"] >= 0
    assert spans[0]["started_at"] is not None
    assert spans[0]["finished_at"] is not None

    snap = event_metrics.snapshot()
    assert snap.events_processed == 1
    assert snap.dispatcher_cycles == 1
    assert snap.events_active_processing == 0


# ── 8. API Endpoints: Health and Trace ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_reliability_health_and_trace_endpoints(async_session: AsyncSession, monkeypatch):
    """GET /reliability/health and GET /reliability/trace/{event_id} return expected payloads."""
    app = create_app()

    # Seed an event record
    e_id = uuid4()
    w_id = uuid4()
    t0 = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(milliseconds=20)
    t2 = t1 + timedelta(milliseconds=15)
    t3 = t2 + timedelta(milliseconds=50)

    record = EventRecord(
        event_id=e_id,
        event_name="ApiTraceTestEvent",
        workspace_id=w_id,
        actor_type="SYSTEM",
        source_subsystem="test",
        category="SYSTEM",
        payload={"event_id": str(e_id)},
        metadata_payload={
            "consumer_spans": [
                {"consumer": "MockConsumer", "stage": 0, "duration_ms": 45.0, "status": "SUCCESS"}
            ]
        },
        occurred_at=t0,
        queued_at=t1,
        processing_started_at=t2,
        completed_at=t3,
        lifecycle_state=EventLifecycleState.COMPLETED.value,
    )
    async_session.add(record)
    await async_session.commit()

    # Override get_db dependency to use async_session
    from app.integrations.postgres.database import get_db

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test /reliability/health
        res_health = await client.get("/reliability/health")
        assert res_health.status_code == 200
        health_data = res_health.json()
        assert health_data["status"] == "healthy"
        assert "operational_metrics" in health_data
        assert "queue_depth" in health_data
        assert health_data["state_distribution"]["COMPLETED"] >= 1

        # Test /reliability/trace/{event_id}
        res_trace = await client.get(f"/reliability/trace/{e_id}")
        assert res_trace.status_code == 200
        trace_data = res_trace.json()
        assert trace_data["event_id"] == str(e_id)
        assert trace_data["event_name"] == "ApiTraceTestEvent"
        assert trace_data["current_state"] == "COMPLETED"
        assert len(trace_data["timeline"]) == 4
        assert len(trace_data["consumer_spans"]) == 1
        assert "latencies" in trace_data
        assert trace_data["latencies"]["end_to_end_ms"] == pytest.approx(85.0)

        # Test 404 for unknown event
        res_404 = await client.get(f"/reliability/trace/{uuid4()}")
        assert res_404.status_code == 404

        # Test 422 for invalid UUID
        res_422 = await client.get("/reliability/trace/not-a-valid-uuid")
        assert res_422.status_code == 422
