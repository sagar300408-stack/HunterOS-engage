"""
Tests for SLAMonitoringEngine.
Models pre-imported via conftest.py to ensure mapper ordering.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.domain.friction.detectors.sla_monitor import SLAMonitoringEngine
from app.domain.friction.models import SLAPolicy, FrictionType


def make_policy(trigger: str, warning_min: int, critical_min: int) -> SLAPolicy:
    """Build an SLAPolicy — safe after conftest model imports."""
    p = SLAPolicy(
        workspace_id=uuid4(),
        policy_name=f"Test Policy ({trigger})",
        event_trigger=trigger,
        target_metric="test_metric",
        warning_threshold_minutes=warning_min,
        critical_threshold_minutes=critical_min,
        is_active=True,
    )
    p.id = uuid4()
    return p


@pytest.mark.asyncio
async def test_no_violations_for_unknown_trigger():
    """Policies with unrecognised triggers produce no events."""
    session = MagicMock()
    engine = SLAMonitoringEngine(session)
    policy = make_policy("unknown.trigger", 30, 120)

    events = await engine._evaluate_policy(uuid4(), policy)
    assert events == []


@pytest.mark.asyncio
async def test_scan_empty_policies_returns_empty():
    session = MagicMock()
    engine = SLAMonitoringEngine(session)

    events = await engine.scan_sla_violations(uuid4(), [])
    assert events == []


@pytest.mark.asyncio
async def test_missed_followup_policy_flags_overdue():
    """Overdue scheduled follow-ups should create MISSED_FOLLOWUP friction events."""
    now = datetime.now(timezone.utc)
    overdue_time = now - timedelta(hours=3)

    mock_fq = MagicMock()
    mock_fq.id = uuid4()
    mock_fq.scheduled_for = overdue_time
    mock_fq.status = "scheduled"
    mock_fq.human_paused = False

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_fq]

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    engine = SLAMonitoringEngine(session)
    policy = make_policy("followup.missed", 30, 60)

    events = await engine._eval_missed_followups(uuid4(), policy)

    assert len(events) == 1
    assert events[0].friction_type == FrictionType.MISSED_FOLLOWUP.value
    assert events[0].score_contribution > 0


@pytest.mark.asyncio
async def test_missed_followup_within_sla_no_event():
    """Follow-ups within SLA threshold should NOT generate friction events."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []  # nothing overdue

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    engine = SLAMonitoringEngine(session)
    policy = make_policy("followup.missed", 30, 60)

    events = await engine._eval_missed_followups(uuid4(), policy)
    assert events == []
