from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.journey.models import (
    JourneyStageCode,
    JourneyState,
    JourneyStatus,
)
from app.domain.journey.query import JourneyQueryEngine
from app.domain.journey.repository import InMemoryJourneyRepository


@pytest.fixture
def query_engine():
    repo = InMemoryJourneyRepository()
    return JourneyQueryEngine(repository=repo)


def test_get_current_journey_state(query_engine):
    j_id = uuid.uuid4()
    state = JourneyState(
        journey_instance_id=j_id,
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        current_stage=JourneyStageCode.NEW_LEAD,
        status=JourneyStatus.ACTIVE,
    )
    query_engine._repository.create_journey(state)

    retrieved = query_engine.get_current_journey_state(j_id)
    assert retrieved is not None
    assert retrieved.journey_instance_id == j_id


def test_get_journeys_by_stage(query_engine):
    j_id = uuid.uuid4()
    state = JourneyState(
        journey_instance_id=j_id,
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        current_stage=JourneyStageCode.NEW_LEAD,
        status=JourneyStatus.ACTIVE,
    )
    query_engine._repository.create_journey(state)

    results = query_engine.get_journeys_by_stage("ws1", JourneyStageCode.NEW_LEAD)
    assert len(results) == 1


def test_get_journeys_by_status(query_engine):
    j_id = uuid.uuid4()
    state = JourneyState(
        journey_instance_id=j_id,
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        current_stage=JourneyStageCode.NEW_LEAD,
        status=JourneyStatus.ACTIVE,
    )
    query_engine._repository.create_journey(state)

    results = query_engine.get_journeys_by_status("ws1", JourneyStatus.ACTIVE)
    assert len(results) == 1


def test_get_recently_transitioned_journeys(query_engine):
    assert hasattr(query_engine, "get_recently_transitioned_journeys")
