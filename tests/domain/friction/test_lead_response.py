"""
Tests for LeadResponseMonitor — idle lead friction detection.
Models pre-imported via conftest.py to ensure mapper ordering.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.domain.friction.detectors.lead_response import (
    LeadResponseMonitor,
    IDLE_LEAD_CRITICAL_HOURS,
    IDLE_LEAD_WARNING_HOURS,
)
from app.domain.friction.models import FrictionType, FrictionSeverity


def make_customer(created_hours_ago: float, name: str = "Test Lead"):
    now = datetime.now(timezone.utc)
    cust = MagicMock()
    cust.id = uuid4()
    cust.workspace_id = uuid4()
    cust.name = name
    cust.phone = "+919999999999"
    cust.created_at = now - timedelta(hours=created_hours_ago)
    cust.last_interaction = None
    return cust


@pytest.mark.asyncio
async def test_critical_idle_lead_generates_friction_event():
    """Lead with no contact for > IDLE_LEAD_CRITICAL_HOURS → CRITICAL event."""
    old_customer = make_customer(created_hours_ago=IDLE_LEAD_CRITICAL_HOURS + 6)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [old_customer]

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.scalar  = AsyncMock(return_value=None)   # no outbound messages

    monitor = LeadResponseMonitor(session)
    events  = await monitor.scan_idle_leads(old_customer.workspace_id)

    assert len(events) == 1
    assert events[0].friction_type  == FrictionType.LEAD_RESPONSE_DELAY.value
    assert events[0].severity        == FrictionSeverity.CRITICAL.value
    assert events[0].score_contribution > 0


@pytest.mark.asyncio
async def test_warning_idle_lead_generates_friction_event():
    """Lead idle for warning threshold → HIGH severity event."""
    warn_customer = make_customer(created_hours_ago=IDLE_LEAD_WARNING_HOURS + 2)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [warn_customer]

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.scalar  = AsyncMock(return_value=None)

    monitor = LeadResponseMonitor(session)
    events  = await monitor.scan_idle_leads(warn_customer.workspace_id)

    assert len(events) >= 1
    assert events[0].friction_type == FrictionType.LEAD_RESPONSE_DELAY.value


@pytest.mark.asyncio
async def test_fresh_lead_does_not_generate_friction():
    """Brand-new lead (within SLA) must NOT produce any friction event."""
    fresh_customer = make_customer(created_hours_ago=0.2)   # 12 minutes old

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fresh_customer]

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.scalar  = AsyncMock(return_value=None)

    monitor = LeadResponseMonitor(session)
    events  = await monitor.scan_idle_leads(fresh_customer.workspace_id)

    assert events == []


@pytest.mark.asyncio
async def test_no_customers_returns_empty():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    monitor = LeadResponseMonitor(session)
    events  = await monitor.scan_idle_leads(uuid4())

    assert events == []


def test_make_event_includes_description():
    """_make_event must produce a valid, populated FrictionEvent."""
    session = MagicMock()
    monitor = LeadResponseMonitor(session)
    cust    = make_customer(created_hours_ago=60)

    event = monitor._make_event(
        workspace_id=cust.workspace_id,
        customer=cust,
        severity=FrictionSeverity.HIGH,
        actual_hours=60.0,
        expected_hours=24.0,
    )

    assert event.description
    assert event.recommendation_hint
    assert event.score_contribution > 0
    assert event.deviation_pct > 0
    assert event.friction_type == FrictionType.LEAD_RESPONSE_DELAY.value
