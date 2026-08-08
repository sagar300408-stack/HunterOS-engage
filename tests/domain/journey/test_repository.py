from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.journey.models import (
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    TransitionType,
)
from app.domain.journey.repository import InMemoryJourneyRepository


@pytest.fixture
def repository():
    return InMemoryJourneyRepository()


@pytest.fixture
def base_state():
    return JourneyState(
        journey_instance_id=uuid.uuid4(),
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        current_stage=JourneyStageCode.NEW_LEAD,
        status=JourneyStatus.ACTIVE,
    )


def test_create_and_get_journey(repository, base_state):
    repository.create_journey(base_state)
    retrieved = repository.get_journey(base_state.journey_instance_id)
    assert retrieved is not None
    assert retrieved.journey_instance_id == base_state.journey_instance_id


def test_save_journey_state_updates_state(repository, base_state):
    repository.create_journey(base_state)

    updated_state = JourneyState(
        journey_instance_id=base_state.journey_instance_id,
        workspace_id="ws1",
        entity_type="CUSTOMER",
        entity_id="lead1",
        current_stage=JourneyStageCode.INTERESTED,
        status=JourneyStatus.ACTIVE,
    )
    repository.save_journey_state(updated_state)

    retrieved = repository.get_journey(base_state.journey_instance_id)
    assert retrieved.current_stage == JourneyStageCode.INTERESTED


def test_append_transition_stores_transitions(repository, base_state):
    repository.create_journey(base_state)
    t_id = uuid.uuid4()
    transition = JourneyStageTransition(
        transition_id=t_id,
        journey_instance_id=base_state.journey_instance_id,
        from_stage=JourneyStageCode.NEW_LEAD,
        to_stage=JourneyStageCode.INTERESTED,
        transition_type=TransitionType.ADVANCE,
        occurred_at=datetime.now(timezone.utc),
        evidence=[],
        confidence=0.9,
    )
    repository.append_transition(base_state.journey_instance_id, transition)
    transitions = repository.get_transitions(base_state.journey_instance_id)
    assert len(transitions) == 1
    assert transitions[0].transition_id == t_id


def test_query_by_stage_returns_matching_journeys(repository, base_state):
    repository.create_journey(base_state)
    results = repository.query_by_stage("ws1", JourneyStageCode.NEW_LEAD)
    assert len(results) == 1

    results_empty = repository.query_by_stage("ws1", JourneyStageCode.INTERESTED)
    assert len(results_empty) == 0


def test_query_by_status_returns_matching_journeys(repository, base_state):
    repository.create_journey(base_state)
    results = repository.query_by_status("ws1", JourneyStatus.ACTIVE)
    assert len(results) == 1


def test_query_by_workspace_returns_all_workspace_journeys(repository, base_state):
    repository.create_journey(base_state)
    results = repository.query_by_workspace("ws1")
    assert len(results) == 1

    results_empty = repository.query_by_workspace("ws2")
    assert len(results_empty) == 0
