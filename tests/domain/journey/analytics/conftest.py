"""
Phase 2.4.4 Analytics Test Fixtures
"""
from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from app.domain.journey.models import (
    JourneyState, JourneyStatus, JourneyStageCode, JourneyType,
    JourneyStageTransition, TransitionType, JourneyTimeline,
)
from app.domain.journey.analytics.models import (
    AnalyticsObservationWindow, JourneyCohortDefinition,
    TrendGranularity, AnalyticsScope,
)
from app.domain.journey.analytics.configuration import (
    build_default_analytics_configuration,
)
from app.domain.journey.analytics.repository import InMemoryJourneyAnalyticsRepository
from app.domain.journey.analytics.cache import InMemoryJourneyAnalyticsCache, NullJourneyAnalyticsCache
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine


@pytest.fixture
def workspace_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def other_workspace_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def observation_window() -> AnalyticsObservationWindow:
    now = datetime.now(timezone.utc)
    return AnalyticsObservationWindow(
        start_at=now - timedelta(days=365),
        end_at=now,
    )


@pytest.fixture
def analytics_config():
    return build_default_analytics_configuration()


@pytest.fixture
def analytics_repository():
    return InMemoryJourneyAnalyticsRepository()


@pytest.fixture
def stats_engine():
    return DescriptiveStatisticsEngine()


def make_journey_state(
    workspace_id: str,
    stage: JourneyStageCode = JourneyStageCode.NEW_LEAD,
    status: JourneyStatus = JourneyStatus.ACTIVE,
    stage_history: List[JourneyStageCode] = None,
    started_days_ago: float = 10.0,
    transitions: List[JourneyStageTransition] = None,
    metadata: dict = None,
) -> JourneyState:
    """Factory for creating test JourneyState instances."""
    now = datetime.now(timezone.utc)
    started = now - timedelta(days=started_days_ago)
    jid = uuid.uuid4()
    return JourneyState(
        journey_instance_id=jid,
        workspace_id=workspace_id,
        entity_type="CUSTOMER",
        entity_id=f"customer-{jid}",
        journey_definition_id=uuid.uuid4(),
        journey_definition_version="v1",
        current_stage=stage,
        previous_stage=None,
        stage_entered_at=started,
        journey_started_at=started,
        last_transition_at=None,
        status=status,
        stage_history=stage_history or [stage],
        transitions=transitions or [],
        metadata=metadata or {},
        timeline=JourneyTimeline(
            timeline_id=uuid.uuid4(),
            journey_instance_id=jid,
            workspace_id=workspace_id,
            events=[],
        ),
    )


def make_transition(
    journey_instance_id: uuid.UUID,
    from_stage: JourneyStageCode,
    to_stage: JourneyStageCode,
    transition_type: TransitionType = TransitionType.ADVANCE,
    days_ago: float = 5.0,
) -> JourneyStageTransition:
    now = datetime.now(timezone.utc)
    return JourneyStageTransition(
        transition_id=uuid.uuid4(),
        journey_instance_id=journey_instance_id,
        from_stage=from_stage,
        to_stage=to_stage,
        transition_type=transition_type,
        occurred_at=now - timedelta(days=days_ago),
        evidence=[],
        confidence=0.85,
        confidence_factors=None,
        reason="Test transition",
    )


@pytest.fixture
def sample_journey_states(workspace_id):
    """10 journeys in various stages."""
    stages = [
        JourneyStageCode.NEW_LEAD,
        JourneyStageCode.NEW_LEAD,
        JourneyStageCode.INTERESTED,
        JourneyStageCode.INTERESTED,
        JourneyStageCode.QUALIFIED,
        JourneyStageCode.NEGOTIATION,
        JourneyStageCode.BOOKING,
        JourneyStageCode.CLOSED_WON,
        JourneyStageCode.CLOSED_LOST,
        JourneyStageCode.INACTIVE,
    ]
    statuses = [
        JourneyStatus.ACTIVE,
        JourneyStatus.ACTIVE,
        JourneyStatus.ACTIVE,
        JourneyStatus.ACTIVE,
        JourneyStatus.ACTIVE,
        JourneyStatus.ACTIVE,
        JourneyStatus.ACTIVE,
        JourneyStatus.COMPLETED,
        JourneyStatus.LOST,
        JourneyStatus.INACTIVE,
    ]
    return [
        make_journey_state(
            workspace_id=workspace_id,
            stage=s,
            status=st,
            stage_history=[JourneyStageCode.NEW_LEAD, s] if s != JourneyStageCode.NEW_LEAD else [s],
            started_days_ago=float(i * 5 + 3),
        )
        for i, (s, st) in enumerate(zip(stages, statuses))
    ]


@pytest.fixture
def sample_transitions(sample_journey_states):
    """Generate transitions for sample journey states."""
    transitions = []
    for j in sample_journey_states:
        if len(j.stage_history) > 1:
            t = make_transition(
                journey_instance_id=j.journey_instance_id,
                from_stage=j.stage_history[0],
                to_stage=j.current_stage,
            )
            transitions.append(t)
    return transitions
