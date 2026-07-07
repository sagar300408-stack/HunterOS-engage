"""
HunterOS Engage — Scheduling API

Phase 5: Scheduling Engine endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth_deps import get_current_user, require_permission
from app.domain.scheduling import service
from app.domain.scheduling import schemas
from app.integrations.postgres.database import get_db_session

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# ── Events ───────────────────────────────────────────────────────────────────

@router.get("/events", response_model=schemas.EventPage)
async def list_events(
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    assigned_to: Optional[UUID] = None,
    customer_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """List scheduled events with filtering and pagination."""
    items, total = await service.list_events(
        session=session,
        workspace_id=user["workspace_id"],
        status=status,
        event_type=event_type,
        assigned_to=assigned_to,
        customer_id=customer_id,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": (page * page_size) < total,
    }


@router.post("/events", response_model=schemas.EventResponse)
async def create_event(
    req: schemas.CreateEventRequest,
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new scheduled event manually."""
    # Ensure workspace_id is set
    req.workspace_id = user["workspace_id"]
    event = await service.create_event(
        session=session,
        req=req,
        actor_id=user["id"]
    )
    return {"event": event, "message": "Event created successfully"}


@router.get("/events/{event_id}", response_model=schemas.EventDetail)
async def get_event(
    event_id: UUID = Path(...),
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Get full details of a specific event."""
    return await service.get_event_detail(session, event_id, user["workspace_id"])


@router.put("/events/{event_id}", response_model=schemas.EventResponse)
async def update_event(
    req: schemas.UpdateEventRequest,
    event_id: UUID = Path(...),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Update event fields (does not change status)."""
    event = await service.update_event(
        session=session,
        event_id=event_id,
        workspace_id=user["workspace_id"],
        req=req,
        actor_id=user["id"]
    )
    return {"event": event, "message": "Event updated successfully"}


@router.post("/events/{event_id}/confirm", response_model=schemas.EventResponse)
async def confirm_event(
    event_id: UUID = Path(...),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Transition event to 'confirmed'."""
    event = await service.transition_event(
        session=session,
        event_id=event_id,
        workspace_id=user["workspace_id"],
        new_status="confirmed",
        actor_id=user["id"]
    )
    return {"event": event, "message": "Event confirmed"}


@router.post("/events/{event_id}/start", response_model=schemas.EventResponse)
async def start_event(
    event_id: UUID = Path(...),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Transition event to 'in_progress'."""
    event = await service.transition_event(
        session=session,
        event_id=event_id,
        workspace_id=user["workspace_id"],
        new_status="in_progress",
        actor_id=user["id"]
    )
    return {"event": event, "message": "Event started"}


@router.post("/events/{event_id}/complete", response_model=schemas.EventResponse)
async def complete_event(
    event_id: UUID = Path(...),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Transition event to 'completed'."""
    event = await service.transition_event(
        session=session,
        event_id=event_id,
        workspace_id=user["workspace_id"],
        new_status="completed",
        actor_id=user["id"]
    )
    return {"event": event, "message": "Event completed"}


@router.post("/events/{event_id}/cancel", response_model=schemas.EventResponse)
async def cancel_event(
    event_id: UUID = Path(...),
    reason: Optional[str] = Query(None),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Cancel an event."""
    event = await service.transition_event(
        session=session,
        event_id=event_id,
        workspace_id=user["workspace_id"],
        new_status="cancelled",
        actor_id=user["id"],
        note=reason
    )
    return {"event": event, "message": "Event cancelled"}


@router.post("/events/{event_id}/reschedule", response_model=schemas.EventResponse)
async def reschedule_event(
    req: schemas.RescheduleEventRequest,
    event_id: UUID = Path(...),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Reschedule an event (creates a new one)."""
    event = await service.reschedule_event(
        session=session,
        event_id=event_id,
        workspace_id=user["workspace_id"],
        req=req,
        actor_id=user["id"]
    )
    return {"event": event, "message": "Event rescheduled"}


@router.post("/events/{event_id}/assign", response_model=schemas.EventResponse)
async def assign_event(
    req: schemas.AssignEventRequest,
    event_id: UUID = Path(...),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Assign an event to a user."""
    event = await service.assign_event(
        session=session,
        event_id=event_id,
        workspace_id=user["workspace_id"],
        req=req,
        actor_id=user["id"]
    )
    return {"event": event, "message": "Event assigned"}


@router.get("/events/{event_id}/audit-log", response_model=list[schemas.EventAuditLogEntry])
async def get_event_audit_log(
    event_id: UUID = Path(...),
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Get the audit log for an event."""
    return await service.get_event_audit_log(session, event_id, user["workspace_id"])


# ── Candidates ───────────────────────────────────────────────────────────────

@router.get("/candidates", response_model=list[schemas.CandidateSummary])
async def list_candidates(
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """List pending AI-proposed scheduling candidates."""
    return await service.list_candidates(session, user["workspace_id"])


@router.get("/candidates/{candidate_id}", response_model=schemas.CandidateDetail)
async def get_candidate(
    candidate_id: UUID = Path(...),
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Get candidate details."""
    return await service.get_candidate_detail(session, candidate_id, user["workspace_id"])


@router.post("/candidates/{candidate_id}/promote", response_model=schemas.PromoteCandidateResponse)
async def promote_candidate(
    candidate_id: UUID = Path(...),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Promote a ready candidate to a ScheduledEvent."""
    event = await service.promote_candidate(
        session=session,
        candidate_id=candidate_id,
        workspace_id=user["workspace_id"],
        actor_id=user["id"]
    )
    # Re-fetch candidate detail to return
    candidate = await service.get_candidate_detail(session, candidate_id, user["workspace_id"])
    return {"candidate": candidate, "event": event, "message": "Candidate promoted"}


@router.post("/candidates/{candidate_id}/abandon")
async def abandon_candidate(
    candidate_id: UUID = Path(...),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Abandon a candidate."""
    await service.abandon_candidate(
        session=session,
        candidate_id=candidate_id,
        workspace_id=user["workspace_id"]
    )
    return {"message": "Candidate abandoned"}


# ── Schedule Views ───────────────────────────────────────────────────────────

@router.get("/schedule/today", response_model=list[schemas.EventSummary])
async def get_today_schedule(
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Get events scheduled for today."""
    return await service.get_today_schedule(session, user["workspace_id"])


@router.get("/schedule/upcoming", response_model=list[schemas.EventSummary])
async def get_upcoming_schedule(
    days: int = Query(7, ge=1, le=30),
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Get upcoming events in the next N days."""
    return await service.get_upcoming_schedule(session, user["workspace_id"], days)


@router.get("/schedule/overview", response_model=schemas.SchedulingOverview)
async def get_schedule_overview(
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Get high-level scheduling KPIs for the dashboard."""
    return await service.get_scheduling_overview(session, user["workspace_id"])


# ── Customer Preferences ─────────────────────────────────────────────────────

@router.get("/customers/{customer_id}/events", response_model=list[schemas.EventSummary])
async def get_customer_events(
    customer_id: UUID = Path(...),
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Get all events for a specific customer."""
    items, _ = await service.list_events(
        session=session,
        workspace_id=user["workspace_id"],
        customer_id=customer_id,
        limit=100,
        offset=0
    )
    return items


@router.get("/customers/{customer_id}/availability", response_model=schemas.AvailabilityPreferencesResponse)
async def get_customer_availability(
    customer_id: UUID = Path(...),
    user: dict = Depends(require_permission("read_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Get availability preferences for a customer."""
    return await service.get_availability_preferences(session, customer_id, user["workspace_id"])


@router.put("/customers/{customer_id}/availability", response_model=schemas.AvailabilityPreferencesResponse)
async def update_customer_availability(
    req: schemas.AvailabilityPreferencesRequest,
    customer_id: UUID = Path(...),
    user: dict = Depends(require_permission("write_schedule")),
    session: AsyncSession = Depends(get_db_session),
):
    """Update availability preferences for a customer."""
    return await service.update_availability_preferences(session, customer_id, user["workspace_id"], req)
