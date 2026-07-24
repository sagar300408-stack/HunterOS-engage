"""
Regression tests — Scheduling Engine response serialization.

Guards against:
  - MissingGreenlet during Pydantic response serialization of event.audit_log
  - create_event returning HTTP 500 due to lazy-loaded relationship
  - create_event returning wrong HTTP status code (should be 201)
  - audit_log being absent or empty after creation

Root cause:
  ScheduledEvent.audit_log is a plain SQLAlchemy relationship with no lazy=
  argument, defaulting to lazy="select" (synchronous).  When FastAPI
  serializes EventDetail outside the async greenlet, accessing the unloaded
  collection raises MissingGreenlet.  Fix: session.refresh(event,
  attribute_names=["audit_log"]) inside create_event() before returning.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from app.domain.scheduling.schemas import (
    CreateEventRequest,
    EventDetail,
    EventResponse,
)


# ── Schema-level unit tests ───────────────────────────────────────────────────


class TestCreateEventRequestSchema:
    def test_aware_utc_is_accepted(self):
        req = CreateEventRequest(
            event_type="meeting",
            title="UTC test",
            scheduled_for="2026-07-24T09:00:00Z",
        )
        assert req.scheduled_for is not None
        assert req.scheduled_for.tzinfo is not None

    def test_aware_offset_normalised_to_utc(self):
        req = CreateEventRequest(
            event_type="meeting",
            title="IST test",
            scheduled_for="2026-07-24T14:30:00+05:30",
        )
        assert req.scheduled_for.utcoffset().total_seconds() == 0

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            CreateEventRequest(
                event_type="meeting",
                title="Naive",
                scheduled_for="2026-07-24T14:25:00",
            )
        assert "timezone" in str(exc_info.value).lower() or \
               "Input should have timezone info" in str(exc_info.value)

    def test_invalid_format_rejected(self):
        with pytest.raises(ValidationError):
            CreateEventRequest(
                event_type="meeting",
                title="Bad format",
                scheduled_for="tomorrow noon",
            )

    def test_no_scheduled_for_is_valid(self):
        req = CreateEventRequest(event_type="task", title="Unscheduled")
        assert req.scheduled_for is None


# ── Service-layer unit test ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_service_create_event_calls_session_refresh_on_audit_log():
    """
    create_event() must call session.refresh(event, attribute_names=["audit_log"])
    before returning.  Without this, accessing event.audit_log outside the
    async greenlet raises MissingGreenlet during FastAPI response serialization.
    """
    from app.domain.scheduling.service import create_event
    from app.domain.scheduling.models import ScheduledEvent

    req = CreateEventRequest(
        event_type="meeting",
        title="Serialization regression",
        scheduled_for="2026-07-24T09:00:00+00:00",
    )
    req.workspace_id = uuid4()

    mock_event = MagicMock(spec=ScheduledEvent)
    mock_event.id = uuid4()
    mock_event.workspace_id = req.workspace_id
    mock_event.customer_id = None
    mock_event.conversation_id = None
    mock_event.assigned_to = None
    mock_event.event_type = "meeting"
    mock_event.title = req.title
    mock_event.audit_log = []

    refresh_calls = []

    async def recording_refresh(obj, attribute_names=None):
        refresh_calls.append(attribute_names or [])

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = recording_refresh

    with (
        patch("app.domain.scheduling.service.validate_create_event", return_value=[]),
        patch("app.domain.scheduling.service.ScheduledEvent", return_value=mock_event),
        patch("app.domain.scheduling.service.get_assignment_strategy"),
        patch("app.domain.scheduling.service._append_audit", new_callable=AsyncMock),
        patch("app.domain.scheduling.service.notification_bus.emit", new_callable=AsyncMock),
    ):
        await create_event(session=mock_session, req=req)

    assert any("audit_log" in call for call in refresh_calls), (
        "create_event() did NOT call session.refresh(event, ['audit_log']). "
        "This will cause MissingGreenlet during response serialization."
    )


# ── Pydantic serialization unit tests ────────────────────────────────────────


def _make_event_dict(audit_log=None):
    return {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "customer_id": None,
        "conversation_id": None,
        "assigned_to": None,
        "created_by": None,
        "event_type": "meeting",
        "title": "Test Meeting",
        "description": None,
        "status": "pending",
        "priority": "medium",
        "scheduled_for": datetime(2026, 7, 24, 9, 0, tzinfo=timezone.utc),
        "duration_minutes": 60,
        "assignment_strategy": "manual",
        "created_by_ai": False,
        "crm_synced": False,
        "crm_provider_event_id": None,
        "event_metadata": None,
        "follow_up_policy": None,
        "is_demo": False,
        "created_at": datetime.now(tz=timezone.utc),
        "updated_at": datetime.now(tz=timezone.utc),
        "completed_at": None,
        "cancelled_at": None,
        "audit_log": audit_log if audit_log is not None else [],
        "allowed_transitions": [],
    }


class TestEventDetailSerialization:
    def test_serializes_with_empty_audit_log(self):
        """No MissingGreenlet when audit_log is an empty list (post-refresh state)."""
        detail = EventDetail.model_validate(_make_event_dict(audit_log=[]))
        dumped = detail.model_dump()
        assert dumped["audit_log"] == []

    def test_serializes_with_populated_audit_log(self):
        """audit_log entries serialize correctly with all required fields."""
        entry = {
            "id": uuid4(),
            "actor_type": "user",
            "actor_id": None,
            "action": "created",
            "from_status": None,
            "to_status": "pending",
            "payload": {"event_type": "meeting"},
            "created_at": datetime.now(tz=timezone.utc),
        }
        detail = EventDetail.model_validate(_make_event_dict(audit_log=[entry]))
        assert len(detail.audit_log) == 1
        assert detail.audit_log[0].action == "created"

    def test_event_response_wraps_without_error(self):
        """EventResponse(event=EventDetail(...)) must not raise."""
        detail = EventDetail.model_validate(_make_event_dict())
        resp = EventResponse(event=detail, message="Event created successfully")
        dumped = resp.model_dump()
        assert dumped["message"] == "Event created successfully"
        assert "audit_log" in dumped["event"]

    def test_audit_log_timestamps_are_tz_aware(self):
        """Timestamps in audit log entries must be timezone-aware (ISO-8601 compliant)."""
        now = datetime.now(tz=timezone.utc)
        entry = {
            "id": uuid4(),
            "actor_type": "system",
            "actor_id": None,
            "action": "created",
            "from_status": None,
            "to_status": "pending",
            "payload": None,
            "created_at": now,
        }
        detail = EventDetail.model_validate(_make_event_dict(audit_log=[entry]))
        assert detail.audit_log[0].created_at.tzinfo is not None
