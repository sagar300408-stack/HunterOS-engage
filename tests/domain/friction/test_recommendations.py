"""
Tests for FrictionRecommendationEngine.
Models pre-imported via conftest.py to ensure mapper ordering.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.friction.recommendations import FrictionRecommendationEngine, _TEMPLATES
from app.domain.friction.models import FrictionEvent, FrictionType, FrictionSeverity


def make_friction_event(friction_type: str, contribution: float = 8.0) -> FrictionEvent:
    """Build a FrictionEvent with given type — ORM models safe after conftest imports."""
    return FrictionEvent(
        id=uuid4(),
        workspace_id=uuid4(),
        friction_type=friction_type,
        severity=FrictionSeverity.HIGH.value,
        score_contribution=contribution,
        description="Test friction event",
    )


@pytest.mark.asyncio
async def test_generates_recommendation_for_known_type():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    engine = FrictionRecommendationEngine(session)
    events = [make_friction_event(FrictionType.LEAD_RESPONSE_DELAY.value)]
    recs = await engine.generate_recommendations(uuid4(), events)

    assert len(recs) == 1
    assert recs[0].generator_name == "FrictionRecommendationEngine"
    assert "Lead Response" in recs[0].title


@pytest.mark.asyncio
async def test_deduplicates_same_friction_type():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    engine = FrictionRecommendationEngine(session)
    events = [
        make_friction_event(FrictionType.APPROVAL_DELAY.value),
        make_friction_event(FrictionType.APPROVAL_DELAY.value),
        make_friction_event(FrictionType.APPROVAL_DELAY.value),
    ]
    recs = await engine.generate_recommendations(uuid4(), events)

    assert len(recs) == 1


@pytest.mark.asyncio
async def test_generates_multiple_recommendations_for_different_types():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    engine = FrictionRecommendationEngine(session)
    events = [
        make_friction_event(FrictionType.LEAD_RESPONSE_DELAY.value),
        make_friction_event(FrictionType.APPROVAL_DELAY.value),
        make_friction_event(FrictionType.WORKFLOW_STALL.value),
    ]
    recs = await engine.generate_recommendations(uuid4(), events)

    assert len(recs) == 3


@pytest.mark.asyncio
async def test_skips_unknown_friction_type():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    engine = FrictionRecommendationEngine(session)
    event = make_friction_event("UNKNOWN_TYPE_XYZ")
    recs = await engine.generate_recommendations(uuid4(), [event])

    assert len(recs) == 0


@pytest.mark.asyncio
async def test_returns_empty_list_for_no_events():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    engine = FrictionRecommendationEngine(session)
    recs = await engine.generate_recommendations(uuid4(), [])

    assert recs == []


def test_all_friction_types_have_templates():
    """Every scored FrictionType must have a recommendation template."""
    scored_types = [
        FrictionType.LEAD_RESPONSE_DELAY.value,
        FrictionType.MISSED_FOLLOWUP.value,
        FrictionType.SLA_VIOLATION.value,
        FrictionType.APPROVAL_DELAY.value,
        FrictionType.WORKFLOW_STALL.value,
        FrictionType.OPPORTUNITY_LEAKAGE.value,
        FrictionType.CUSTOMER_INACTIVITY.value,
    ]
    for ftype in scored_types:
        assert ftype in _TEMPLATES, f"Missing template for friction type: {ftype}"


def test_templates_have_required_fields():
    required = {"title", "summary", "actions", "expected_impact",
                "category", "impact_category", "priority", "risk", "score"}
    for ftype, template in _TEMPLATES.items():
        missing = required - set(template.keys())
        assert not missing, f"Template '{ftype}' missing fields: {missing}"
