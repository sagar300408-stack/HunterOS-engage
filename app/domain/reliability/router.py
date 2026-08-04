from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.integrations.postgres.database import get_db
from app.api.v1.auth_deps import get_current_user, RequirePermissions
from app.domain.reliability.models import PerformanceBenchmark, ReliabilityEvent, DeploymentRecord
from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState
from app.events.lifecycle.manager import LifecycleManager
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Reliability & Performance"])

@router.get("/performance/benchmarks", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_benchmarks(db: AsyncSession = Depends(get_db)):
    """
    Returns the latest performance benchmark runs and SLO compliance.
    """
    stmt = select(PerformanceBenchmark).order_by(PerformanceBenchmark.timestamp.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/reliability/status", dependencies=[Depends(RequirePermissions("view_all"))])
async def reliability_status(db: AsyncSession = Depends(get_db)):
    """
    Returns current platform health, including active degradations or failovers.
    """
    stmt = select(ReliabilityEvent).where(ReliabilityEvent.resolved == False)
    result = await db.execute(stmt)
    active_events = result.scalars().all()
    
    return {
        "status": "degraded" if active_events else "healthy",
        "active_events": active_events
    }

@router.post("/reliability/failover", dependencies=[Depends(RequirePermissions("platform_admin"))])
async def trigger_manual_failover(service_name: str, db: AsyncSession = Depends(get_db)):
    """
    Manually triggers a failover for a specific service.
    """
    event = ReliabilityEvent(
        event_type="failover",
        service_name=service_name,
        description="Manual failover triggered by admin"
    )
    db.add(event)
    await db.commit()
    return {"status": "failover_initiated"}

@router.get("/deployments", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_deployments(db: AsyncSession = Depends(get_db)):
    """
    Returns deployment history.
    """
    stmt = select(DeploymentRecord).order_by(DeploymentRecord.deployed_at.desc()).limit(50)
    result = await db.execute(stmt)
    return result.scalars().all()


# --- Event Observability & Tracing Endpoints ---

@router.get("/reliability/health", summary="Event Pipeline Health and Metrics")
async def pipeline_health(session: AsyncSession = Depends(get_db)):
    """
    Returns aggregate event platform health and operational metrics.
    Includes in-memory rate counters and real-time DB queue depth/states.
    """
    from datetime import datetime, timezone
    from sqlalchemy import func
    from app.events.observability.metrics import event_metrics

    # Query DB state counts for accurate queue depth and terminal counts
    state_stmt = (
        select(EventRecord.lifecycle_state, func.count(EventRecord.event_id))
        .group_by(EventRecord.lifecycle_state)
    )
    res = await session.execute(state_stmt)
    state_counts = dict(res.all())

    persisted = state_counts.get(EventLifecycleState.PERSISTED.value, 0)
    retrying = state_counts.get(EventLifecycleState.RETRYING.value, 0)
    processing = state_counts.get(EventLifecycleState.PROCESSING.value, 0)
    completed = state_counts.get(EventLifecycleState.COMPLETED.value, 0)
    dead_letter = state_counts.get(EventLifecycleState.DEAD_LETTER.value, 0)
    queue_depth = persisted + retrying

    snapshot = event_metrics.snapshot()
    status = "degraded" if dead_letter > 0 else "healthy"

    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queue_depth": queue_depth,
        "active_processing": processing or snapshot.events_active_processing,
        "dead_letter_count": dead_letter,
        "completed_count": completed,
        "operational_metrics": snapshot.to_dict(),
        "state_distribution": {
            "PERSISTED": persisted,
            "QUEUED": state_counts.get(EventLifecycleState.QUEUED.value, 0),
            "PROCESSING": processing,
            "RETRYING": retrying,
            "COMPLETED": completed,
            "DEAD_LETTER": dead_letter,
            "REPLAYED": state_counts.get(EventLifecycleState.REPLAYED.value, 0),
        },
    }


@router.get("/reliability/trace/{event_id}", summary="Reconstruct Event Execution History & Trace")
async def get_event_trace(event_id: str, session: AsyncSession = Depends(get_db)):
    """
    Reconstructs an event's complete execution history, including:
      - Identity and Context headers (trace_id, correlation_id, workspace_id)
      - Immutable lifecycle timeline with transition timestamps
      - Consumer spans with execution policies, stages, status, and duration
      - Computed latency metrics across all lifecycle phases
      - Full retry and replay history
    """
    from uuid import UUID
    from app.events.observability.timeline import build_trace_response

    try:
        uid = UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid event_id format")

    stmt = select(EventRecord).where(EventRecord.event_id == uid)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Event not found")

    return build_trace_response(record)

# --- DLQ Endpoints ---

@router.get("/reliability/dlq", summary="List Dead Letter Queue Events")
async def list_dlq(session: AsyncSession = Depends(get_db)):
    """
    Returns a list of all events that have reached the DEAD_LETTER state.
    """
    stmt = select(EventRecord).where(EventRecord.lifecycle_state == EventLifecycleState.DEAD_LETTER.value)
    result = await session.execute(stmt)
    records = result.scalars().all()
    
    return {
        "status": "ok",
        "dead_letters": [
            {
                "event_id": str(r.event_id),
                "event_name": r.event_name,
                "error_detail": r.error_detail,
                "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
                "retry_count": r.retry_count
            }
            for r in records
        ]
    }

@router.post("/reliability/dlq/{event_id}/replay", summary="Replay a DLQ Event")
async def replay_dlq_event(event_id: str, session: AsyncSession = Depends(get_db)):
    """
    Requeues a DEAD_LETTER or COMPLETED event for re-processing.

    Lifecycle path:
        DEAD_LETTER | COMPLETED → REPLAYED → PERSISTED
        (Outbox Dispatcher picks it up on next poll: PERSISTED → QUEUED → PROCESSING)

    The REPLAYED → PERSISTED step is an intentional bypass of the state machine:
    REPLAYED is a momentary audit marker. The dispatcher re-enters the normal
    lifecycle from PERSISTED so queued_at and processing_started_at are
    freshly stamped on the new dispatch cycle.
    """
    from uuid import UUID

    try:
        uid = UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid event_id format")

    stmt = select(EventRecord).where(EventRecord.event_id == uid)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Event not found")

    if record.lifecycle_state not in (
        EventLifecycleState.DEAD_LETTER.value,
        EventLifecycleState.COMPLETED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Event is in '{record.lifecycle_state}' state; "
                "only DEAD_LETTER or COMPLETED events can be replayed"
            ),
        )

    # Step 1 — DEAD_LETTER | COMPLETED → REPLAYED (via manager: validated + logged)
    await LifecycleManager.replay(session, uid)

    # Step 2 — REPLAYED → PERSISTED (intentional direct reset).
    # REPLAYED is an audit marker only; the event must re-enter the outbox as
    # PERSISTED so the dispatcher stamps a fresh queued_at on pickup.
    # retry_count and error_detail are cleared so the event gets a clean slate.
    record.lifecycle_state = EventLifecycleState.PERSISTED.value
    record.retry_count = 0
    record.error_detail = None
    record.next_retry_at = None

    from app.events.observability.metrics import event_metrics
    event_metrics.increment("replay_bypasses")

    logger.info(
        "replay_duplicate_bypass",
        event_id=event_id,
        event_name=record.event_name,
        workspace_id=str(record.workspace_id) if record.workspace_id else None,
        idempotency_key=record.idempotency_key,
        from_state="REPLAYED",
    )

    logger.info(
        "event_replay_reset_to_persisted",
        event_id=event_id,
        event_name=record.event_name,
    )

    await session.commit()

    return {
        "status": "ok",
        "message": (
            f"Event {event_id} reset to PERSISTED — "
            "Outbox Dispatcher will re-queue it on the next poll"
        ),
    }


# --- Event Partitioning & Ordering Observability Endpoints ---

@router.get("/reliability/partitions", summary="Get Event Partitioning Observability & Lock Status")
async def get_partition_metrics(session: AsyncSession = Depends(get_db)):
    """
    Returns real-time partition observability metrics, active locks, and fairness statistics.
    """
    from datetime import datetime, timezone
    from sqlalchemy import func
    from app.events.partitioning.lock_manager import get_lock_manager
    from app.events.partitioning.config import partition_config
    from app.events.observability.metrics import event_metrics

    lock_mgr = get_lock_manager()
    active_locks = lock_mgr.get_active_locks()
    lock_stats = lock_mgr.get_stats()
    metrics_snap = event_metrics.snapshot()

    # Query active pending partitions from DB
    stmt = (
        select(
            EventRecord.partition_key,
            func.count(EventRecord.event_id).label("event_count"),
            func.min(EventRecord.occurred_at).label("oldest_event")
        )
        .where(
            EventRecord.lifecycle_state.in_([
                EventLifecycleState.PERSISTED.value,
                EventLifecycleState.RETRYING.value,
            ])
        )
        .group_by(EventRecord.partition_key)
    )
    result = await session.execute(stmt)
    rows = result.all()

    now = datetime.now(timezone.utc)
    total_pending_partitions = len(rows)
    locked_keys = set(active_locks.keys())

    waiting_list = []
    active_list = []
    largest_name = None
    largest_size = 0
    oldest_waiting_name = None
    oldest_waiting_age_sec = 0.0

    for r in rows:
        p_key = r.partition_key or "unpartitioned"
        cnt = r.event_count
        oldest_ts = r.oldest_event

        if cnt > largest_size:
            largest_size = cnt
            largest_name = p_key

        if p_key in locked_keys:
            waiting_list.append({"partition_key": p_key, "pending_events": cnt})
            if oldest_ts:
                if oldest_ts.tzinfo is None:
                    oldest_ts = oldest_ts.replace(tzinfo=timezone.utc)
                age = (now - oldest_ts).total_seconds()
                if age > oldest_waiting_age_sec:
                    oldest_waiting_age_sec = age
                    oldest_waiting_name = p_key
        else:
            active_list.append({"partition_key": p_key, "pending_events": cnt})

    total_events = sum(r.event_count for r in rows)
    avg_per_partition = (total_events / total_pending_partitions) if total_pending_partitions > 0 else 0.0
    utilization = (
        len(active_list) / partition_config.max_active_partitions
        if partition_config.max_active_partitions > 0 else 0.0
    )

    return {
        "timestamp": now.isoformat(),
        "total_pending_partitions": total_pending_partitions,
        "active_partitions_count": len(active_list),
        "waiting_partitions_count": len(waiting_list),
        "active_partitions": active_list,
        "waiting_partitions": waiting_list,
        "largest_partition": {
            "name": largest_name,
            "size": largest_size,
        },
        "average_events_per_partition": round(avg_per_partition, 2),
        "oldest_waiting_partition": {
            "name": oldest_waiting_name,
            "wait_duration_seconds": round(oldest_waiting_age_sec, 2),
        },
        "partition_utilization": round(utilization, 4),
        "active_locks": [
            {
                "partition_key": lease.partition_key,
                "lease_token": lease.lease_token[:12] + "...",
                "acquired_at": lease.acquired_at.isoformat(),
                "expires_at": lease.expires_at.isoformat(),
                "timeout_seconds": lease.timeout_seconds,
            }
            for lease in active_locks.values()
        ],
        "lock_metrics": lock_stats,
        "fairness_policy": partition_config.fairness_policy,
        "scheduler_cycles": metrics_snap.scheduler_cycles,
    }


@router.post("/reliability/partitions/{partition_key}/unlock", summary="Force Release Partition Lock")
async def force_unlock_partition(partition_key: str):
    """
    Forcefully unlocks a partition in emergency scenarios or manual operator recovery.
    """
    from app.events.partitioning.lock_manager import get_lock_manager
    lock_mgr = get_lock_manager()
    released = lock_mgr.force_release(partition_key)

    if not released:
        raise HTTPException(
            status_code=404,
            detail=f"Partition '{partition_key}' does not hold an active lock",
        )

    logger.warning("partition_force_unlocked_via_api", partition_key=partition_key)
    return {
        "status": "ok",
        "message": f"Partition '{partition_key}' lock was successfully force released",
    }


# --- Event Priority, Flow Control & Backpressure Observability Endpoints ---

@router.get("/reliability/priorities", summary="Get Event Priority Metrics & Distribution")
async def get_priority_metrics(session: AsyncSession = Depends(get_db)):
    """
    Returns priority distribution across pending outbox events, cumulative dispatch counters,
    virtual aging promotions, and flow control state.
    """
    from datetime import datetime, timezone
    from sqlalchemy import func
    from app.events.observability.metrics import event_metrics
    from app.events.priority.priority import PriorityLevel, PriorityResolver

    stmt = (
        select(EventRecord)
        .where(
            EventRecord.lifecycle_state.in_([
                EventLifecycleState.PERSISTED.value,
                EventLifecycleState.RETRYING.value,
            ])
        )
    )
    res = await session.execute(stmt)
    records = list(res.scalars().all())

    priority_counts = {p.value: 0 for p in PriorityLevel}
    for r in records:
        prio = PriorityResolver.resolve_priority(r)
        priority_counts[prio.value] = priority_counts.get(prio.value, 0) + 1

    snapshot = event_metrics.snapshot()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pending_priority_distribution": priority_counts,
        "dispatched_by_priority": {
            "CRITICAL": snapshot.priority_critical_dispatched,
            "HIGH": snapshot.priority_high_dispatched,
            "NORMAL": snapshot.priority_normal_dispatched,
            "LOW": snapshot.priority_low_dispatched,
            "BACKGROUND": snapshot.priority_background_dispatched,
        },
        "aging_promotions_total": snapshot.priority_aging_promotions,
        "backpressure_events_total": snapshot.dispatcher_backpressure_events,
        "throttled_events_total": snapshot.dispatcher_throttled_events,
        "queue_health_score": snapshot.queue_health_score,
        "worker_utilization_pct": snapshot.worker_utilization,
    }


@router.get("/reliability/health/queue", summary="Get Real-Time Queue Health & Load State Snapshot")
async def get_queue_health_snapshot(session: AsyncSession = Depends(get_db)):
    """
    Computes a point-in-time composite Queue Health Snapshot including throughput,
    oldest event latency, worker utilization, health score, and system load state.
    """
    from datetime import datetime, timezone
    from app.events.priority.health import QueueHealthMonitor

    stmt = (
        select(EventRecord)
        .where(
            EventRecord.lifecycle_state.in_([
                EventLifecycleState.PERSISTED.value,
                EventLifecycleState.RETRYING.value,
            ])
        )
    )
    res = await session.execute(stmt)
    records = list(res.scalars().all())

    monitor = QueueHealthMonitor()
    snapshot = monitor.compute_snapshot(records, now=datetime.now(timezone.utc))

    return snapshot.to_dict()


@router.get("/reliability/cluster", summary="Get Distributed Dispatcher Cluster Status & Topology")
async def get_cluster_status(session: AsyncSession = Depends(get_db)):
    """
    Returns current cluster topology, membership epoch, active leader,
    heartbeat timestamps, ring version, and cluster health score.
    """
    from datetime import datetime, timezone
    from app.events.observability.metrics import event_metrics

    snapshot = event_metrics.snapshot()

    return {
        "status": "healthy" if snapshot.cluster_health_score >= 80 else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cluster_epoch": snapshot.cluster_epoch,
        "ring_version": snapshot.current_ring_version,
        "membership_changes_total": snapshot.membership_changes,
        "cluster_nodes_total": snapshot.cluster_nodes,
        "healthy_nodes_total": snapshot.healthy_nodes,
        "leader_changes_total": snapshot.leader_changes,
        "leadership_acquisitions_total": snapshot.leadership_acquisitions,
        "leadership_losses_total": snapshot.leadership_losses,
        "dispatcher_heartbeats_total": snapshot.dispatcher_heartbeats,
        "dispatcher_failures_total": snapshot.dispatcher_failures,
        "cluster_health_score": snapshot.cluster_health_score,
        "cluster_uptime_seconds": snapshot.cluster_uptime,
        "dispatcher_assignments": snapshot.dispatcher_assignments,
        "dispatcher_load_pct": snapshot.dispatcher_load,
    }


# ── Distributed Tracing & Execution Intelligence Endpoints ────────────────────

@router.get("/reliability/traces", summary="List Distributed Traces (Paginated)")
async def list_distributed_traces(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    workspace_id: Optional[str] = None,
):
    """
    Returns paginated list of recent distributed trace snapshots with status and duration metrics.
    """
    from app.events.tracing import trace_manager

    traces = trace_manager.storage.list_traces(
        limit=limit,
        offset=offset,
        status=status,
        workspace_id=workspace_id,
    )
    return {
        "total": trace_manager.storage.get_total_traces_count(),
        "limit": limit,
        "offset": offset,
        "count": len(traces),
        "traces": [t.to_dict() for t in traces],
    }


@router.get("/reliability/traces/search", summary="Search Distributed Traces")
async def search_distributed_traces(
    trace_id: Optional[str] = None,
    event_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    dispatcher_id: Optional[str] = None,
    worker_id: Optional[str] = None,
    consumer_name: Optional[str] = None,
    partition_key: Optional[str] = None,
    priority: Optional[int] = None,
    status: Optional[str] = None,
    min_duration_ms: Optional[float] = None,
    max_duration_ms: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    Searches distributed traces by multi-dimensional criteria including trace ID, event ID,
    workspace, correlation chain, consumer, partition, status, and duration bounds.
    """
    from app.events.tracing import trace_manager, TraceSearchQuery

    query = TraceSearchQuery(
        trace_id=trace_id,
        event_id=event_id,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        dispatcher_id=dispatcher_id,
        worker_id=worker_id,
        consumer_name=consumer_name,
        partition_key=partition_key,
        priority=priority,
        status=status,
        min_duration_ms=min_duration_ms,
        max_duration_ms=max_duration_ms,
        limit=limit,
        offset=offset,
    )
    result = trace_manager.search_traces(query)
    return result.to_dict()


@router.get("/reliability/traces/{trace_id}", summary="Get Full Distributed Trace Snapshot")
async def get_distributed_trace(trace_id: str):
    """
    Reconstructs and returns the full distributed trace snapshot including
    hierarchical span tree, timeline, critical path, and latency breakdown.
    """
    from app.events.tracing import trace_manager

    snapshot = trace_manager.get_trace(trace_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Trace with ID '{trace_id}' not found")

    return snapshot.to_dict()


@router.get("/reliability/traces/{trace_id}/timeline", summary="Get Distributed Trace Execution Timeline")
async def get_distributed_trace_timeline(trace_id: str):
    """
    Returns the granular chronological execution timeline, stage transitions, and wait times for a trace.
    """
    from app.events.tracing import trace_manager

    snapshot = trace_manager.get_trace(trace_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Trace with ID '{trace_id}' not found")

    if not snapshot.timeline:
        raise HTTPException(status_code=404, detail="Execution timeline not available for this trace")

    return snapshot.timeline.to_dict()


@router.get("/reliability/traces/{trace_id}/critical-path", summary="Get Trace Critical Path & Bottlenecks")
async def get_distributed_trace_critical_path(trace_id: str):
    """
    Returns the critical path analysis, sequential dependencies, and blocking duration for a trace.
    """
    from app.events.tracing import trace_manager

    snapshot = trace_manager.get_trace(trace_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Trace with ID '{trace_id}' not found")

    timeline = snapshot.timeline
    critical_duration = timeline.critical_path_duration_ms if timeline else (snapshot.root_span.duration_ms or 0.0)
    blocking_time = timeline.blocking_time_ms if timeline else 0.0

    return {
        "trace_id": trace_id,
        "critical_path_spans": snapshot.critical_path_spans,
        "critical_path_duration_ms": round(critical_duration, 3),
        "blocking_time_ms": round(blocking_time, 3),
        "total_duration_ms": round(snapshot.root_span.duration_ms or 0.0, 3),
        "concurrency_savings_ms": round(max(0.0, (snapshot.root_span.duration_ms or 0.0) - critical_duration), 3),
    }


# ── Execution Intelligence & Analytics Endpoints ───────────────────────────────

@router.get("/reliability/intelligence", summary="Get Full Execution Intelligence Overview")
async def get_execution_intelligence():
    """
    Returns the comprehensive execution intelligence report including multi-dimensional
    health scores, detected root causes, active bottlenecks, patterns, and recommendations.
    """
    from app.events.intelligence import intelligence_engine

    report = intelligence_engine.get_intelligence_report()
    return report.to_dict()


@router.get("/reliability/intelligence/root-causes", summary="Get Detected Root Cause Analyses")
async def get_intelligence_root_causes(limit: int = 50):
    """
    Returns recent root cause failure analyses and failure propagation chains.
    """
    from app.events.intelligence import intelligence_engine

    root_causes = intelligence_engine.get_root_causes(limit=limit)
    return {
        "total_root_causes": len(root_causes),
        "root_causes": [rc.to_dict() for rc in root_causes],
    }


@router.get("/reliability/intelligence/bottlenecks", summary="Get Identified Execution Bottlenecks")
async def get_intelligence_bottlenecks(limit: int = 50):
    """
    Returns identified execution bottlenecks across consumers, dispatchers, queues, and database.
    """
    from app.events.intelligence import intelligence_engine

    bottlenecks = intelligence_engine.get_bottlenecks(limit=limit)
    return {
        "total_bottlenecks": len(bottlenecks),
        "bottlenecks": [bn.to_dict() for bn in bottlenecks],
    }


@router.get("/reliability/intelligence/recommendations", summary="Get Actionable Operational Recommendations")
async def get_intelligence_recommendations(limit: int = 50):
    """
    Returns prioritized, evidence-based recommendations to optimize pipeline throughput and reliability.
    """
    from app.events.intelligence import intelligence_engine

    recommendations = intelligence_engine.get_recommendations(limit=limit)
    return {
        "total_recommendations": len(recommendations),
        "recommendations": [rec.to_dict() for rec in recommendations],
    }


@router.get("/reliability/intelligence/health", summary="Get Multi-Dimensional Platform Health")
async def get_intelligence_health():
    """
    Returns multi-dimensional health scores (0-100) across Dispatcher, Worker, Consumer, Partition, Retry, Latency, and Failure subsystems.
    """
    from app.events.intelligence import intelligence_engine

    health_report = intelligence_engine.get_health_report()
    return health_report.to_dict()


@router.get("/reliability/intelligence/trends", summary="Get Historical Performance & Latency Trends")
async def get_intelligence_trends():
    """
    Returns rolling statistical percentiles (P50, P90, P95, P99), throughput trends, and error rates.
    """
    from app.events.intelligence import intelligence_engine

    trends = intelligence_engine.get_historical_trends()
    return trends.to_dict()


# ── Live Operational Diagnostics & Runtime Inspection Endpoints ─────────────

@router.get("/reliability/runtime", summary="Get Complete Point-in-Time Runtime Snapshot")
async def get_runtime_snapshot(session: AsyncSession = Depends(get_db)):
    """
    Returns a complete, consistent runtime snapshot across all event subsystems
    generated from a single logical observation point (snapshot_id & snapshot_timestamp).
    """
    from app.events.diagnostics import diagnostics_engine

    snapshot = await diagnostics_engine.get_runtime_snapshot(session=session)
    return snapshot.model_dump()


@router.get("/reliability/runtime/workers", summary="Get Live Worker Diagnostics")
async def get_runtime_workers(session: AsyncSession = Depends(get_db)):
    """
    Returns live background worker diagnostics including active/idle counts,
    utilization %, throughput, task assignments, and failure counts.
    """
    from app.events.diagnostics import diagnostics_engine

    workers = await diagnostics_engine.get_worker_diagnostics(session=session)
    return workers.model_dump()


@router.get("/reliability/runtime/dispatchers", summary="Get Live Dispatcher Diagnostics")
async def get_runtime_dispatchers(session: AsyncSession = Depends(get_db)):
    """
    Returns live outbox dispatcher diagnostics including active dispatchers,
    leader status, poll frequency, scheduling latency, and queue depth.
    """
    from app.events.diagnostics import diagnostics_engine

    dispatchers = await diagnostics_engine.get_dispatcher_diagnostics(session=session)
    return dispatchers.model_dump()


@router.get("/reliability/runtime/queues", summary="Get Live Queue Diagnostics")
async def get_runtime_queues(session: AsyncSession = Depends(get_db)):
    """
    Returns live queue lifecycle distribution diagnostics across pending, queued,
    processing, retrying, dead-letter, and replay states.
    """
    from app.events.diagnostics import diagnostics_engine

    queues = await diagnostics_engine.get_queue_diagnostics(session=session)
    return queues.model_dump()


@router.get("/reliability/runtime/partitions", summary="Get Live Partition Diagnostics")
async def get_runtime_partitions(session: AsyncSession = Depends(get_db)):
    """
    Returns live partition diagnostics including active/waiting counts, backlog depths,
    hottest partitions, and oldest uncommitted event age.
    """
    from app.events.diagnostics import diagnostics_engine

    partitions = await diagnostics_engine.get_partition_diagnostics(session=session)
    return partitions.model_dump()


@router.get("/reliability/runtime/locks", summary="Get Live Partition Lock Diagnostics")
async def get_runtime_locks(session: AsyncSession = Depends(get_db)):
    """
    Returns live partition lock diagnostics including active leases, expired locks,
    lock owner distributions, and contention counts.
    """
    from app.events.diagnostics import diagnostics_engine

    locks = await diagnostics_engine.get_lock_diagnostics(session=session)
    return locks.model_dump()


@router.get("/reliability/runtime/consumers", summary="Get Live Consumer Diagnostics")
async def get_runtime_consumers(session: AsyncSession = Depends(get_db)):
    """
    Returns live consumer diagnostics including execution counts, failure rates,
    average and P95 latencies, slowest consumers, and dependency graph.
    """
    from app.events.diagnostics import diagnostics_engine

    consumers = await diagnostics_engine.get_consumer_diagnostics(session=session)
    return consumers.model_dump()


@router.get("/reliability/runtime/health", summary="Get Live Runtime Health Summary")
async def get_runtime_health(session: AsyncSession = Depends(get_db)):
    """
    Returns live runtime health summary with multi-dimensional subsystem scores,
    resource utilization, capacity estimation, and early warning indicators.
    """
    from app.events.diagnostics import diagnostics_engine

    health = await diagnostics_engine.get_runtime_health(session=session)
    return health.model_dump()






