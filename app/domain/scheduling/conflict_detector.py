"""
HunterOS Engage — Schedule Conflict Detector

Detects time overlaps when assigning a representative to a scheduled event.

Phase 5:
  - check_conflicts() returns existing overlapping events
  - suggested_slots is always empty (Phase 6 feature)

Phase 6:
  - suggested_slots will contain AI-generated alternative time slots
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConflictResult:
    """Result of a conflict check."""
    has_conflict:         bool
    conflicting_events:   list  = field(default_factory=list)   # list[ScheduledEvent]
    suggested_slots:      list  = field(default_factory=list)   # list[datetime] — Phase 6
    checked_user_id:      Optional[UUID] = None
    checked_time:         Optional[datetime] = None
    checked_duration_min: Optional[int] = None


async def check_conflicts(
    session:          AsyncSession,
    assigned_to:      UUID,
    scheduled_for:    datetime,
    duration_minutes: int = 60,
    exclude_event_id: Optional[UUID] = None,
    workspace_id:     Optional[UUID] = None,
) -> ConflictResult:
    """
    Query scheduled_events for overlapping events assigned to the same user.

    Overlap detection:
        Event A overlaps Event B if:
            A.start < B.end  AND  A.end > B.start

    Args:
        session:          Active async DB session.
        assigned_to:      User UUID to check.
        scheduled_for:    Proposed event start time (timezone-aware).
        duration_minutes: Proposed event duration in minutes (default 60).
        exclude_event_id: Exclude this event ID (for reschedule checks).
        workspace_id:     Scope check to this workspace.

    Returns:
        ConflictResult with has_conflict=True and conflicting events if overlap found.
    """
    from app.domain.scheduling.models import ScheduledEvent

    # Ensure timezone-aware
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)

    event_end = scheduled_for + timedelta(minutes=duration_minutes)

    # Non-terminal statuses that can conflict
    active_statuses = ["pending", "confirmed", "in_progress"]

    q = (
        select(ScheduledEvent)
        .where(
            and_(
                ScheduledEvent.assigned_to  == assigned_to,
                ScheduledEvent.status.in_(active_statuses),
                ScheduledEvent.scheduled_for.isnot(None),
                # Overlap: existing_start < proposed_end AND existing_end > proposed_start
                # We approximate existing_end as scheduled_for + duration_minutes (or +60 if null)
                ScheduledEvent.scheduled_for < event_end,
            )
        )
    )

    if exclude_event_id:
        q = q.where(ScheduledEvent.id != exclude_event_id)

    if workspace_id:
        q = q.where(ScheduledEvent.workspace_id == workspace_id)

    result = await session.execute(q)
    candidates = result.scalars().all()

    # Filter by actual end-time overlap (more precise)
    conflicting = []
    for ev in candidates:
        ev_start = ev.scheduled_for
        if ev_start.tzinfo is None:
            ev_start = ev_start.replace(tzinfo=timezone.utc)
        ev_duration = ev.duration_minutes or 60
        ev_end = ev_start + timedelta(minutes=ev_duration)

        # Overlap condition
        if ev_start < event_end and ev_end > scheduled_for:
            conflicting.append(ev)

    has_conflict = len(conflicting) > 0

    if has_conflict:
        logger.warning(
            "schedule_conflict_detected",
            assigned_to=str(assigned_to),
            scheduled_for=scheduled_for.isoformat(),
            conflicting_count=len(conflicting),
        )
    else:
        logger.debug(
            "schedule_no_conflict",
            assigned_to=str(assigned_to),
            scheduled_for=scheduled_for.isoformat(),
        )

    return ConflictResult(
        has_conflict=has_conflict,
        conflicting_events=conflicting,
        suggested_slots=[],     # Phase 6: populated by AI slot suggester
        checked_user_id=assigned_to,
        checked_time=scheduled_for,
        checked_duration_min=duration_minutes,
    )
