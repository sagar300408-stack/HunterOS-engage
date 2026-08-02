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
