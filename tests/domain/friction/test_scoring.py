"""
Tests for FrictionScoreEngine — Business Friction Score computation.
Uses MagicMock for snapshot objects to avoid ORM mapper dependency.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.domain.friction.scoring import FrictionScoreEngine, WEIGHT_CONFIG
from app.domain.friction.models import FrictionType


def make_repo(open_by_type: dict, previous_score=None):
    repo = MagicMock()
    repo.get_open_events_by_type = AsyncMock(return_value=open_by_type)
    if previous_score is not None:
        snap = MagicMock()
        snap.score = previous_score
        repo.get_latest_score = AsyncMock(return_value=snap)
    else:
        repo.get_latest_score = AsyncMock(return_value=None)
    return repo


@pytest.mark.asyncio
async def test_zero_friction_when_no_open_events():
    repo = make_repo({})
    engine = FrictionScoreEngine(repo)
    snapshot = await engine.compute_score(uuid4())

    assert snapshot.score == 0.0
    assert snapshot.trend == "STABLE"
    assert snapshot.contributors == {}


@pytest.mark.asyncio
async def test_score_increases_with_friction_events():
    repo = make_repo({
        FrictionType.LEAD_RESPONSE_DELAY.value: 3,   # 3 × 4.0 = 12.0
        FrictionType.APPROVAL_DELAY.value: 2,          # 2 × 6.0 = 12.0
    })
    engine = FrictionScoreEngine(repo)
    snapshot = await engine.compute_score(uuid4())

    assert snapshot.score == pytest.approx(24.0, abs=0.1)
    assert snapshot.contributors[FrictionType.LEAD_RESPONSE_DELAY.value] == pytest.approx(12.0)
    assert snapshot.contributors[FrictionType.APPROVAL_DELAY.value] == pytest.approx(12.0)


@pytest.mark.asyncio
async def test_score_capped_at_100():
    open_by_type = {ftype: 100 for ftype in WEIGHT_CONFIG}
    repo = make_repo(open_by_type)
    engine = FrictionScoreEngine(repo)
    snapshot = await engine.compute_score(uuid4())

    assert snapshot.score <= 100.0


@pytest.mark.asyncio
async def test_per_type_contribution_capped_at_max_weight():
    repo = make_repo({FrictionType.LEAD_RESPONSE_DELAY.value: 1000})
    engine = FrictionScoreEngine(repo)
    snapshot = await engine.compute_score(uuid4())

    # Max weight for LEAD_RESPONSE_DELAY is 20
    assert snapshot.contributors.get(FrictionType.LEAD_RESPONSE_DELAY.value) == pytest.approx(20.0)


@pytest.mark.asyncio
async def test_trend_deteriorating_when_score_increases():
    repo = make_repo(
        {FrictionType.SLA_VIOLATION.value: 3},
        previous_score=5.0
    )
    engine = FrictionScoreEngine(repo)
    snapshot = await engine.compute_score(uuid4())

    assert snapshot.trend == "DETERIORATING"
    assert snapshot.score_delta is not None
    assert snapshot.score_delta > 0


@pytest.mark.asyncio
async def test_trend_improving_when_score_decreases():
    repo = make_repo({}, previous_score=50.0)
    engine = FrictionScoreEngine(repo)
    snapshot = await engine.compute_score(uuid4())

    assert snapshot.trend == "IMPROVING"
    assert snapshot.score_delta < 0


@pytest.mark.asyncio
async def test_trend_stable_when_change_less_than_1():
    repo = make_repo(
        {FrictionType.MISSED_FOLLOWUP.value: 1},   # 1 × 3.0 = 3.0 pts
        previous_score=3.0
    )
    engine = FrictionScoreEngine(repo)
    snapshot = await engine.compute_score(uuid4())

    assert snapshot.trend == "STABLE"


@pytest.mark.asyncio
async def test_snapshot_has_workspace_id():
    wid = uuid4()
    repo = make_repo({})
    engine = FrictionScoreEngine(repo)
    snapshot = await engine.compute_score(wid)

    assert snapshot.workspace_id == wid
