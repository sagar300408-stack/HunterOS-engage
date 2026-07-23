"""
HunterOS Engage — Scheduling Service

All database operations for the scheduling domain.

Design:
  - Every public function is async and accepts AsyncSession
  - State machine transitions go through state_machine.transition() only
  - Every mutation appends an EventAuditLog row — callers never write audit logs directly
  - The notification_bus is called after every commit-worthy mutation
  - All queries are scoped to workspace_id where applicable
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.scheduling.assignment import get_assignment_strategy
from app.domain.scheduling.conflict_detector import ConflictResult, check_conflicts
from app.domain.scheduling.models import (
    CustomerAvailabilityPreferences,
    EventAuditLog,
    ScheduledEvent,
    SchedulingCandidate,
)
from app.domain.scheduling.notification_bus import NotificationEvent, notification_bus
from app.domain.scheduling.resolver import ResolverDecision, scheduling_resolver
from app.domain.scheduling.schemas import (
    AssignEventRequest,
    AvailabilityPreferencesRequest,
    ConflictCheckRequest,
    CreateEventRequest,
    RescheduleEventRequest,
    TransitionEventRequest,
    UpdateCandidateRequest,
    UpdateEventRequest,
)
from app.domain.scheduling.state_machine import (
    InvalidTransitionError,
    get_allowed_transitions,
    transition,
)
from app.domain.scheduling.validators import validate_create_event, get_missing_fields
from app.domain.security.models import DEFAULT_WORKSPACE_ID
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


async def _append_audit(
    session:      AsyncSession,
    event:        ScheduledEvent,
    action:       str,
    actor_type:   str = "system",
    actor_id:     Optional[UUID] = None,
    from_status:  Optional[str] = None,
    to_status:    Optional[str] = None,
    payload:      Optional[dict] = None,
) -> None:
    """
    Append one immutable audit log row for a ScheduledEvent mutation.

    Internal helper — callers never write EventAuditLog directly.
    """
    log = EventAuditLog(
        workspace_id=event.workspace_id,
        event_id=event.id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        payload=payload,
    )
    session.add(log)


# ── Event CRUD ────────────────────────────────────────────────────────────────


async def create_event(
    session:      AsyncSession,
    req:          CreateEventRequest,
    actor_type:   str = "user",
    actor_id:     Optional[UUID] = None,
    is_demo:      bool = False,
) -> ScheduledEvent:
    """
    Create a new ScheduledEvent from a CreateEventRequest.

    Validates the request, assigns the event if assigned_to is provided,
    and appends an audit log entry.

    Args:
        session:    Active async DB session.
        req:        Validated CreateEventRequest.
        actor_type: "user" | "ai" | "system"
        actor_id:   UUID of the acting user (None for AI/system).
        is_demo:    Flag for demo data isolation.

    Returns:
        The newly created ScheduledEvent (flushed, not committed).

    Raises:
        ValueError: If validation fails.
    """
    errors = validate_create_event(
        event_type=req.event_type,
        title=req.title,
        metadata=req.metadata,
        scheduled_for=req.scheduled_for,
        priority=req.priority,
    )
    if errors:
        raise ValueError(f"Invalid event: {'; '.join(errors)}")

    workspace = req.workspace_id or DEFAULT_WORKSPACE_ID

    event = ScheduledEvent(
        workspace_id=workspace,
        customer_id=req.customer_id,
        conversation_id=req.conversation_id,
        event_type=req.event_type,
        title=req.title,
        description=req.description,
        status="pending",
        priority=req.priority,
        scheduled_for=req.scheduled_for,
        duration_minutes=req.duration_minutes,
        assignment_strategy=req.assignment_strategy,
        created_by_ai=(actor_type == "ai"),
        created_by=actor_id,
        event_metadata=req.metadata,
        is_demo=is_demo,
    )

    # Apply assignment if specified
    if req.assigned_to:
        strategy = get_assignment_strategy("manual", user_id=req.assigned_to)
        assigned_uid = await strategy.assign(session, event, workspace)
        event.assigned_to = assigned_uid
        event.assignment_strategy = req.assignment_strategy

    session.add(event)
    await session.flush()

    # Audit log
    await _append_audit(
        session,
        event,
        action="created",
        actor_type=actor_type,
        actor_id=actor_id,
        to_status="pending",
        payload={
            "event_type": event.event_type,
            "title": event.title,
            "assigned_to": str(event.assigned_to) if event.assigned_to else None,
        },
    )
    await session.flush()

    logger.info(
        "scheduling_event_created",
        event_id=str(event.id),
        event_type=event.event_type,
        actor_type=actor_type,
        customer_id=str(event.customer_id) if event.customer_id else None,
    )

    await notification_bus.emit(NotificationEvent(
        event_type="event_created",
        scheduled_event_id=event.id,
        workspace_id=event.workspace_id,
        customer_id=event.customer_id,
        assigned_to_user_id=event.assigned_to,
        payload={"event_type": event.event_type, "title": event.title},
    ))

    return event


async def get_event(
    session:      AsyncSession,
    event_id:     UUID,
    workspace_id: Optional[UUID] = None,
) -> Optional[ScheduledEvent]:
    """
    Fetch a ScheduledEvent by ID with its audit log eagerly loaded.

    Returns None if not found or workspace mismatch.
    """
    q = (
        select(ScheduledEvent)
        .where(ScheduledEvent.id == event_id)
        .options(selectinload(ScheduledEvent.audit_log))
    )
    if workspace_id:
        q = q.where(ScheduledEvent.workspace_id == workspace_id)

    result = await session.execute(q)
    return result.scalar_one_or_none()


async def list_events(
    session:      AsyncSession,
    workspace_id: Optional[UUID] = None,
    customer_id:  Optional[UUID] = None,
    assigned_to:  Optional[UUID] = None,
    event_type:   Optional[str]  = None,
    status:       Optional[str]  = None,
    from_date:    Optional[datetime] = None,
    to_date:      Optional[datetime] = None,
    page:         int = 1,
    page_size:    int = 20,
) -> tuple[list[ScheduledEvent], int]:
    """
    Paginated list of ScheduledEvents with optional filters.

    Returns (events, total_count).
    """
    conditions = []
    if workspace_id:
        conditions.append(ScheduledEvent.workspace_id == workspace_id)
    if customer_id:
        conditions.append(ScheduledEvent.customer_id == customer_id)
    if assigned_to:
        conditions.append(ScheduledEvent.assigned_to == assigned_to)
    if event_type:
        conditions.append(ScheduledEvent.event_type == event_type)
    if status:
        conditions.append(ScheduledEvent.status == status)
    if from_date:
        conditions.append(ScheduledEvent.scheduled_for >= from_date)
    if to_date:
        conditions.append(ScheduledEvent.scheduled_for <= to_date)

    base_q = select(ScheduledEvent)
    if conditions:
        base_q = base_q.where(and_(*conditions))

    # Total count
    count_q = select(func.count()).select_from(base_q.subquery())
    count_result = await session.execute(count_q)
    total = count_result.scalar_one()

    # Paginated results ordered newest first
    offset = (page - 1) * page_size
    items_q = (
        base_q
        .order_by(desc(ScheduledEvent.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(items_q)
    events = list(result.scalars().all())

    return events, total


async def update_event(
    session:      AsyncSession,
    event_id:     UUID,
    req:          UpdateEventRequest,
    actor_type:   str = "user",
    actor_id:     Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
) -> Optional[ScheduledEvent]:
    """
    Apply a partial update (PATCH) to a ScheduledEvent.

    Only non-None fields in req are applied.
    Status changes are NOT handled here — use transition_event().

    Returns None if the event is not found.
    """
    event = await get_event(session, event_id, workspace_id=workspace_id)
    if not event:
        return None

    before: dict = {}
    after:  dict = {}

    if req.title is not None and req.title != event.title:
        before["title"] = event.title
        after["title"]  = req.title
        event.title = req.title

    if req.description is not None:
        before["description"] = event.description
        after["description"]  = req.description
        event.description = req.description

    if req.assigned_to is not None and req.assigned_to != event.assigned_to:
        before["assigned_to"] = str(event.assigned_to) if event.assigned_to else None
        after["assigned_to"]  = str(req.assigned_to)
        event.assigned_to = req.assigned_to

    if req.priority is not None and req.priority != event.priority:
        before["priority"] = event.priority
        after["priority"]  = req.priority
        event.priority = req.priority

    if req.scheduled_for is not None:
        before["scheduled_for"] = event.scheduled_for.isoformat() if event.scheduled_for else None
        after["scheduled_for"]  = req.scheduled_for.isoformat()
        event.scheduled_for = req.scheduled_for

    if req.duration_minutes is not None:
        before["duration_minutes"] = event.duration_minutes
        after["duration_minutes"]  = req.duration_minutes
        event.duration_minutes = req.duration_minutes

    if req.metadata is not None:
        # Merge metadata (shallow merge — caller sends full dict to replace)
        before["metadata"] = event.event_metadata
        after["metadata"]  = req.metadata
        event.event_metadata = req.metadata

    event.updated_at = _now()
    await session.flush()

    if after:
        await _append_audit(
            session,
            event,
            action="updated",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"before": before, "after": after},
        )
        await session.flush()

    logger.info(
        "scheduling_event_updated",
        event_id=str(event_id),
        changes=list(after.keys()),
    )

    return event


async def transition_event(
    session:      AsyncSession,
    event_id:     UUID,
    req:          TransitionEventRequest,
    actor_type:   str = "user",
    actor_id:     Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
) -> ScheduledEvent:
    """
    Apply a state machine transition to a ScheduledEvent.

    Raises:
        ValueError:            If the event is not found.
        InvalidTransitionError: If the transition is not allowed.
    """
    event = await get_event(session, event_id, workspace_id=workspace_id)
    if not event:
        raise ValueError(f"ScheduledEvent {event_id} not found")

    prev_status = event.status
    transition(event, req.new_status)   # raises InvalidTransitionError on invalid

    now = _now()
    if req.new_status == "completed":
        event.completed_at = now
    elif req.new_status == "cancelled":
        event.cancelled_at = now

    event.updated_at = now
    await session.flush()

    await _append_audit(
        session,
        event,
        action=req.new_status,
        actor_type=actor_type,
        actor_id=actor_id,
        from_status=prev_status,
        to_status=req.new_status,
        payload={"note": req.note} if req.note else None,
    )
    await session.flush()

    logger.info(
        "scheduling_event_transitioned",
        event_id=str(event_id),
        from_status=prev_status,
        to_status=req.new_status,
    )

    await notification_bus.emit(NotificationEvent(
        event_type=f"event_{req.new_status}",
        scheduled_event_id=event.id,
        workspace_id=event.workspace_id,
        customer_id=event.customer_id,
        assigned_to_user_id=event.assigned_to,
    ))

    return event


async def assign_event(
    session:      AsyncSession,
    event_id:     UUID,
    req:          AssignEventRequest,
    actor_type:   str = "user",
    actor_id:     Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
) -> Optional[ScheduledEvent]:
    """
    Assign (or reassign) a ScheduledEvent to a representative.

    Applies the named assignment strategy. In Phase 5, only "manual" is
    fully implemented; other strategies raise NotImplementedError.

    Returns None if the event is not found.
    """
    event = await get_event(session, event_id, workspace_id=workspace_id)
    if not event:
        return None

    prev_assigned = str(event.assigned_to) if event.assigned_to else None

    strategy = get_assignment_strategy(req.assignment_strategy, user_id=req.assigned_to)
    new_uid   = await strategy.assign(session, event, event.workspace_id)

    event.assigned_to         = new_uid
    event.assignment_strategy = req.assignment_strategy
    event.updated_at          = _now()
    await session.flush()

    await _append_audit(
        session,
        event,
        action="assigned",
        actor_type=actor_type,
        actor_id=actor_id,
        payload={
            "from_assigned_to": prev_assigned,
            "to_assigned_to":   str(new_uid) if new_uid else None,
            "strategy":         req.assignment_strategy,
            "note":             req.note,
        },
    )
    await session.flush()

    logger.info(
        "scheduling_event_assigned",
        event_id=str(event_id),
        assigned_to=str(new_uid),
        strategy=req.assignment_strategy,
    )

    await notification_bus.emit(NotificationEvent(
        event_type="event_assigned",
        scheduled_event_id=event.id,
        workspace_id=event.workspace_id,
        customer_id=event.customer_id,
        assigned_to_user_id=new_uid,
    ))

    return event


async def reschedule_event(
    session:      AsyncSession,
    event_id:     UUID,
    req:          RescheduleEventRequest,
    actor_type:   str = "user",
    actor_id:     Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
) -> tuple[ScheduledEvent, ScheduledEvent]:
    """
    Reschedule an event.

    Flow:
      1. Transition original event → "rescheduled" (terminal).
      2. Create new event copying all fields, with updated scheduled_for.
      3. Append audit entries on both events.

    Returns:
        (original_event, new_event)

    Raises:
        ValueError:            If the event is not found.
        InvalidTransitionError: If the original cannot be rescheduled.
    """
    original = await get_event(session, event_id, workspace_id=workspace_id)
    if not original:
        raise ValueError(f"ScheduledEvent {event_id} not found")

    prev_status = original.status
    transition(original, "rescheduled")
    original.updated_at = _now()
    await session.flush()

    await _append_audit(
        session,
        original,
        action="rescheduled",
        actor_type=actor_type,
        actor_id=actor_id,
        from_status=prev_status,
        to_status="rescheduled",
        payload={
            "reason":           req.reason,
            "new_scheduled_for": req.new_scheduled_for.isoformat(),
        },
    )
    await session.flush()

    # Create the replacement event
    new_event = ScheduledEvent(
        workspace_id=original.workspace_id,
        customer_id=original.customer_id,
        conversation_id=original.conversation_id,
        assigned_to=original.assigned_to,
        created_by=actor_id,
        event_type=original.event_type,
        title=original.title,
        description=original.description,
        status="pending",
        priority=original.priority,
        scheduled_for=req.new_scheduled_for,
        duration_minutes=req.new_duration_minutes or original.duration_minutes,
        assignment_strategy=original.assignment_strategy,
        created_by_ai=original.created_by_ai,
        event_metadata=original.event_metadata,
        is_demo=original.is_demo,
    )
    session.add(new_event)
    await session.flush()

    await _append_audit(
        session,
        new_event,
        action="created",
        actor_type=actor_type,
        actor_id=actor_id,
        to_status="pending",
        payload={
            "rescheduled_from": str(original.id),
            "reason":           req.reason,
        },
    )
    await session.flush()

    logger.info(
        "scheduling_event_rescheduled",
        original_id=str(original.id),
        new_id=str(new_event.id),
        new_time=req.new_scheduled_for.isoformat(),
    )

    await notification_bus.emit(NotificationEvent(
        event_type="event_rescheduled",
        scheduled_event_id=new_event.id,
        workspace_id=new_event.workspace_id,
        customer_id=new_event.customer_id,
        assigned_to_user_id=new_event.assigned_to,
        payload={
            "original_event_id": str(original.id),
            "new_scheduled_for": req.new_scheduled_for.isoformat(),
        },
    ))

    return original, new_event


async def conflict_check(
    session: AsyncSession,
    req:     ConflictCheckRequest,
) -> ConflictResult:
    """
    Run a conflict check for a proposed assignment + time.

    Pure read operation — no mutations.
    """
    return await check_conflicts(
        session=session,
        assigned_to=req.assigned_to,
        scheduled_for=req.scheduled_for,
        duration_minutes=req.duration_minutes,
        exclude_event_id=req.exclude_event_id,
        workspace_id=req.workspace_id,
    )


# ── Candidate lifecycle ───────────────────────────────────────────────────────


async def create_candidate_from_resolver(
    session:        AsyncSession,
    decision:       ResolverDecision,
    customer_id:    UUID,
    conversation_id: Optional[UUID] = None,
    workspace_id:   Optional[UUID] = None,
) -> SchedulingCandidate:
    """
    Create a SchedulingCandidate from a ResolverDecision.

    Called by the pipeline after intent extraction when can_create_immediately=False.

    The candidate tracks which fields still need to be collected from the customer.
    The AI is directed to ask for them via the system prompt injection.

    Returns:
        The newly created SchedulingCandidate (flushed, not committed).
    """
    ws = workspace_id or DEFAULT_WORKSPACE_ID
    status = "ready" if decision.can_create_immediately else "pending_info"

    candidate = SchedulingCandidate(
        workspace_id=ws,
        customer_id=customer_id,
        conversation_id=conversation_id,
        suggested_event_type=decision.suggested_event_type,
        suggested_title=decision.suggested_title,
        resolver_output={
            "required_fields":         decision.required_fields,
            "optional_fields":         decision.optional_fields,
            "default_priority":        decision.default_priority,
            "default_duration_minutes": decision.default_duration_minutes,
            "confidence":              decision.confidence,
        },
        collected_data=decision.collected_fields,
        missing_fields=decision.missing_fields,
        status=status,
        created_by_ai=True,
    )
    session.add(candidate)
    await session.flush()

    logger.info(
        "scheduling_candidate_created",
        candidate_id=str(candidate.id),
        event_type=decision.suggested_event_type,
        status=status,
        missing=decision.missing_fields,
    )

    return candidate


async def get_active_candidate(
    session:        AsyncSession,
    customer_id:    UUID,
    workspace_id:   Optional[UUID] = None,
) -> Optional[SchedulingCandidate]:
    """
    Return the most recent active candidate for a customer.

    Active = status in ("pending_info", "ready").
    Returns None if no active candidate exists.

    Used by the pipeline to inject the PENDING SCHEDULING REQUEST block
    into the AI system prompt.
    """
    q = (
        select(SchedulingCandidate)
        .where(
            and_(
                SchedulingCandidate.customer_id == customer_id,
                SchedulingCandidate.status.in_(["pending_info", "ready"]),
            )
        )
        .order_by(desc(SchedulingCandidate.created_at))
        .limit(1)
    )
    if workspace_id:
        q = q.where(SchedulingCandidate.workspace_id == workspace_id)

    result = await session.execute(q)
    return result.scalar_one_or_none()


async def update_candidate_fields(
    session:      AsyncSession,
    candidate_id: UUID,
    req:          UpdateCandidateRequest,
    workspace_id: Optional[UUID] = None,
) -> Optional[SchedulingCandidate]:
    """
    Merge newly collected fields into a SchedulingCandidate.

    Recomputes missing_fields and transitions to 'ready' if all required fields
    are now present.

    Returns None if the candidate is not found or not updatable.
    """
    q = select(SchedulingCandidate).where(SchedulingCandidate.id == candidate_id)
    if workspace_id:
        q = q.where(SchedulingCandidate.workspace_id == workspace_id)

    result = await session.execute(q)
    candidate = result.scalar_one_or_none()

    if not candidate or candidate.status not in ("pending_info", "ready"):
        return None

    # Merge collected data
    merged = {**(candidate.collected_data or {}), **req.collected_data}
    candidate.collected_data = merged

    # Recompute missing fields
    still_missing = get_missing_fields(candidate.suggested_event_type, merged)
    candidate.missing_fields = still_missing

    if not still_missing and candidate.status == "pending_info":
        candidate.status = "ready"
        logger.info(
            "scheduling_candidate_ready",
            candidate_id=str(candidate_id),
            event_type=candidate.suggested_event_type,
        )

    candidate.updated_at = _now()
    await session.flush()

    return candidate


async def promote_candidate(
    session:      AsyncSession,
    candidate_id: UUID,
    actor_type:   str = "ai",
    actor_id:     Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
    is_demo:      bool = False,
) -> tuple[SchedulingCandidate, ScheduledEvent]:
    """
    Promote a 'ready' SchedulingCandidate to a ScheduledEvent.

    Preconditions:
        - candidate.status == "ready"
        - candidate.missing_fields is empty

    Flow:
      1. Validate candidate is ready.
      2. Build a CreateEventRequest from the candidate.
      3. create_event() — creates the ScheduledEvent.
      4. Mark candidate as 'promoted', link promoted_event_id.

    Returns:
        (candidate, new_event)

    Raises:
        ValueError: If not ready or not found.
    """
    q = select(SchedulingCandidate).where(SchedulingCandidate.id == candidate_id)
    if workspace_id:
        q = q.where(SchedulingCandidate.workspace_id == workspace_id)

    result = await session.execute(q)
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise ValueError(f"SchedulingCandidate {candidate_id} not found")

    if candidate.status != "ready":
        raise ValueError(
            f"Candidate {candidate_id} is not ready for promotion "
            f"(status={candidate.status}, missing={candidate.missing_fields})"
        )

    # Build CreateEventRequest from candidate data
    resolver_out = candidate.resolver_output or {}

    from app.domain.scheduling.schemas import CreateEventRequest as CER
    create_req = CER(
        event_type=candidate.suggested_event_type,
        title=candidate.suggested_title or candidate.suggested_event_type.title(),
        customer_id=candidate.customer_id,
        conversation_id=candidate.conversation_id,
        priority=resolver_out.get("default_priority", "medium"),
        duration_minutes=resolver_out.get("default_duration_minutes", 30),
        metadata=candidate.collected_data,
        workspace_id=candidate.workspace_id,
    )

    new_event = await create_event(
        session,
        create_req,
        actor_type=actor_type,
        actor_id=actor_id,
        is_demo=is_demo,
    )

    # Mark candidate as promoted
    candidate.status           = "promoted"
    candidate.promoted_event_id = new_event.id
    candidate.updated_at       = _now()
    await session.flush()

    logger.info(
        "scheduling_candidate_promoted",
        candidate_id=str(candidate_id),
        event_id=str(new_event.id),
        event_type=new_event.event_type,
    )

    return candidate, new_event


async def abandon_candidate(
    session:      AsyncSession,
    candidate_id: UUID,
    reason:       Optional[str] = None,
    workspace_id: Optional[UUID] = None,
) -> Optional[SchedulingCandidate]:
    """
    Mark a candidate as 'abandoned' — will no longer inject into AI prompts.

    Returns None if not found or already terminal.
    """
    q = select(SchedulingCandidate).where(SchedulingCandidate.id == candidate_id)
    if workspace_id:
        q = q.where(SchedulingCandidate.workspace_id == workspace_id)

    result = await session.execute(q)
    candidate = result.scalar_one_or_none()

    if not candidate or candidate.status in ("promoted", "abandoned"):
        return None

    candidate.status     = "abandoned"
    candidate.updated_at = _now()
    await session.flush()

    logger.info(
        "scheduling_candidate_abandoned",
        candidate_id=str(candidate_id),
        reason=reason,
    )

    return candidate


# ── CustomerAvailabilityPreferences ──────────────────────────────────────────


async def get_or_create_availability_prefs(
    session:      AsyncSession,
    customer_id:  UUID,
    workspace_id: Optional[UUID] = None,
) -> CustomerAvailabilityPreferences:
    """
    Return existing availability preferences or create a default row.

    The default row uses Asia/Kolkata timezone with all preferences unset.
    """
    q = select(CustomerAvailabilityPreferences).where(
        CustomerAvailabilityPreferences.customer_id == customer_id
    )
    if workspace_id:
        q = q.where(CustomerAvailabilityPreferences.workspace_id == workspace_id)

    result = await session.execute(q)
    prefs = result.scalar_one_or_none()

    if prefs is None:
        ws = workspace_id or DEFAULT_WORKSPACE_ID
        prefs = CustomerAvailabilityPreferences(
            workspace_id=ws,
            customer_id=customer_id,
        )
        session.add(prefs)
        await session.flush()

    return prefs


async def update_availability_prefs(
    session:      AsyncSession,
    customer_id:  UUID,
    req:          AvailabilityPreferencesRequest,
    workspace_id: Optional[UUID] = None,
) -> CustomerAvailabilityPreferences:
    """
    Update (or upsert) customer availability preferences.

    Only non-None fields in req are applied.
    """
    prefs = await get_or_create_availability_prefs(session, customer_id, workspace_id)

    if req.preferred_time_of_day is not None:
        prefs.preferred_time_of_day = req.preferred_time_of_day
    if req.unavailable_days is not None:
        prefs.unavailable_days = req.unavailable_days
    if req.preferred_meeting_mode is not None:
        prefs.preferred_meeting_mode = req.preferred_meeting_mode
    if req.timezone is not None:
        prefs.timezone = req.timezone
    if req.notes is not None:
        prefs.notes = req.notes

    prefs.updated_at = _now()
    await session.flush()

    return prefs


# ── Overview / dashboard aggregates ──────────────────────────────────────────


async def get_scheduling_overview(
    session:      AsyncSession,
    workspace_id: Optional[UUID] = None,
) -> dict:
    """
    Compute scheduling KPI metrics for the dashboard overview widget.

    Returns a dict matching SchedulingOverview schema.
    """
    ws_filter = (
        [ScheduledEvent.workspace_id == workspace_id]
        if workspace_id else []
    )

    # Total events
    total_q = select(func.count(ScheduledEvent.id)).where(*ws_filter)
    total = (await session.execute(total_q)).scalar_one()

    # Count by status
    async def count_status(st: str) -> int:
        q = select(func.count(ScheduledEvent.id)).where(
            ScheduledEvent.status == st, *ws_filter
        )
        return (await session.execute(q)).scalar_one()

    pending     = await count_status("pending")
    confirmed   = await count_status("confirmed")
    in_progress = await count_status("in_progress")

    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    completed_today_q = select(func.count(ScheduledEvent.id)).where(
        ScheduledEvent.status == "completed",
        ScheduledEvent.completed_at >= today_start,
        *ws_filter,
    )
    completed_today = (await session.execute(completed_today_q)).scalar_one()

    cancelled_today_q = select(func.count(ScheduledEvent.id)).where(
        ScheduledEvent.status == "cancelled",
        ScheduledEvent.cancelled_at >= today_start,
        *ws_filter,
    )
    cancelled_today = (await session.execute(cancelled_today_q)).scalar_one()

    # Active candidates
    cand_filter = (
        [SchedulingCandidate.workspace_id == workspace_id]
        if workspace_id else []
    )
    active_cands_q = select(func.count(SchedulingCandidate.id)).where(
        SchedulingCandidate.status.in_(["pending_info", "ready"]),
        *cand_filter,
    )
    active_candidates = (await session.execute(active_cands_q)).scalar_one()

    # Events this week
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_q = select(func.count(ScheduledEvent.id)).where(
        ScheduledEvent.scheduled_for >= week_start,
        ScheduledEvent.scheduled_for < week_start + timedelta(days=7),
        *ws_filter,
    )
    events_this_week = (await session.execute(week_q)).scalar_one()

    # Overdue events (scheduled_for < now AND status in active statuses)
    overdue_q = select(func.count(ScheduledEvent.id)).where(
        ScheduledEvent.scheduled_for < now,
        ScheduledEvent.scheduled_for.isnot(None),
        ScheduledEvent.status.in_(["pending", "confirmed"]),
        *ws_filter,
    )
    overdue_events = (await session.execute(overdue_q)).scalar_one()

    # AI-created percentage
    ai_q = select(func.count(ScheduledEvent.id)).where(
        ScheduledEvent.created_by_ai.is_(True),
        *ws_filter,
    )
    ai_count = (await session.execute(ai_q)).scalar_one()
    ai_pct = round((ai_count / total * 100) if total > 0 else 0.0, 1)

    return {
        "total_events":          total,
        "pending":               pending,
        "confirmed":             confirmed,
        "in_progress":           in_progress,
        "completed_today":       completed_today,
        "cancelled_today":       cancelled_today,
        "active_candidates":     active_candidates,
        "events_this_week":      events_this_week,
        "overdue_events":        overdue_events,
        "ai_created_percentage": ai_pct,
    }


# ── Pipeline integration ──────────────────────────────────────────────────────


async def process_intent_for_scheduling(
    session:         AsyncSession,
    customer_id:     UUID,
    conversation_id: Optional[UUID],
    next_action:     Optional[str],
    buying_stage:    Optional[str],
    urgency:         Optional[str],
    confidence:      float,
    customer_name:   Optional[str] = None,
    extracted_data:  Optional[dict] = None,
    workspace_id:    Optional[UUID] = None,
    is_demo:         bool = False,
) -> Optional[SchedulingCandidate]:
    """
    Pipeline hook — called after intent extraction.

    Flow:
      1. Check if an active candidate already exists for this customer.
         If yes, the candidate collection continues — return existing candidate.
      2. Run the resolver. If no match, return None.
      3. If can_create_immediately → create ScheduledEvent directly (no candidate).
      4. Otherwise → create SchedulingCandidate for field collection.

    Returns the active/new candidate, or None if no scheduling action is warranted.
    """
    # Step 1: Check for existing active candidate
    existing = await get_active_candidate(session, customer_id, workspace_id)
    if existing:
        logger.debug(
            "scheduling_pipeline_existing_candidate",
            candidate_id=str(existing.id),
            status=existing.status,
            missing=existing.missing_fields,
        )
        return existing

    # Step 2: Run the resolver
    decision = scheduling_resolver.resolve(
        next_action=next_action,
        buying_stage=buying_stage,
        urgency=urgency,
        confidence=confidence,
        customer_name=customer_name,
        extracted_data=extracted_data,
    )

    if decision is None:
        return None

    # Step 3: Immediate creation (all fields present)
    if decision.can_create_immediately:
        from app.domain.scheduling.schemas import CreateEventRequest as CER
        create_req = CER(
            event_type=decision.suggested_event_type,
            title=decision.suggested_title,
            customer_id=customer_id,
            conversation_id=conversation_id,
            priority=decision.default_priority,
            duration_minutes=decision.default_duration_minutes,
            metadata=decision.collected_fields,
            workspace_id=workspace_id,
        )
        await create_event(
            session,
            create_req,
            actor_type="ai",
            is_demo=is_demo,
        )
        logger.info(
            "scheduling_pipeline_event_created_immediately",
            event_type=decision.suggested_event_type,
            customer_id=str(customer_id),
        )
        return None   # no candidate needed

    # Step 4: Create candidate for field collection
    candidate = await create_candidate_from_resolver(
        session,
        decision,
        customer_id=customer_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
    )

    return candidate


async def get_event_detail(
    session: AsyncSession,
    event_id: UUID,
    workspace_id: UUID,
) -> Optional[ScheduledEvent]:
    return await get_event(session, event_id, workspace_id)


async def get_event_audit_log(
    session: AsyncSession,
    event_id: UUID,
    workspace_id: UUID,
) -> list[EventAuditLog]:
    q = (
        select(EventAuditLog)
        .where(
            EventAuditLog.event_id == event_id,
            EventAuditLog.workspace_id == workspace_id,
        )
        .order_by(EventAuditLog.created_at.desc())
    )
    result = await session.execute(q)
    return list(result.scalars().all())


async def list_candidates(
    session: AsyncSession,
    workspace_id: UUID,
) -> list[SchedulingCandidate]:
    q = (
        select(SchedulingCandidate)
        .where(
            SchedulingCandidate.workspace_id == workspace_id,
            SchedulingCandidate.status.in_(["pending_info", "ready"]),
        )
        .order_by(desc(SchedulingCandidate.created_at))
    )
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_candidate_detail(
    session: AsyncSession,
    candidate_id: UUID,
    workspace_id: UUID,
) -> Optional[SchedulingCandidate]:
    q = (
        select(SchedulingCandidate)
        .where(
            SchedulingCandidate.id == candidate_id,
            SchedulingCandidate.workspace_id == workspace_id,
        )
    )
    result = await session.execute(q)
    return result.scalar_one_or_none()


async def get_today_schedule(
    session: AsyncSession,
    workspace_id: UUID,
) -> list[ScheduledEvent]:
    now = _now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    q = (
        select(ScheduledEvent)
        .where(
            ScheduledEvent.workspace_id == workspace_id,
            ScheduledEvent.scheduled_for >= start_of_day,
            ScheduledEvent.scheduled_for < end_of_day,
        )
        .order_by(ScheduledEvent.scheduled_for.asc())
    )
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_upcoming_schedule(
    session: AsyncSession,
    workspace_id: UUID,
    days: int,
) -> list[ScheduledEvent]:
    now = _now()
    end_time = now + timedelta(days=days)
    
    q = (
        select(ScheduledEvent)
        .where(
            ScheduledEvent.workspace_id == workspace_id,
            ScheduledEvent.scheduled_for >= now,
            ScheduledEvent.scheduled_for < end_time,
        )
        .order_by(ScheduledEvent.scheduled_for.asc())
    )
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_availability_preferences(
    session: AsyncSession,
    customer_id: UUID,
    workspace_id: UUID,
) -> CustomerAvailabilityPreferences:
    return await get_or_create_availability_prefs(session, customer_id, workspace_id)


async def update_availability_preferences(
    session: AsyncSession,
    customer_id: UUID,
    workspace_id: UUID,
    req: AvailabilityPreferencesRequest,
) -> CustomerAvailabilityPreferences:
    return await update_availability_prefs(session, customer_id, req, workspace_id)
