from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.domain.journey.models import (
    JourneyTimeline,
    JourneyTimelineEvent,
    TimelineEventType,
)
from app.domain.journey.timeline import JourneyTimelineBuilder


def test_journey_timeline_builder_create_journey_started_event():
    builder = JourneyTimelineBuilder()
    j_id = uuid.uuid4()
    timeline = builder.create_initial_timeline(j_id, datetime.now(timezone.utc))
    assert timeline is not None
    assert len(timeline.events) == 1
    assert timeline.events[0].event_type == TimelineEventType.JOURNEY_STARTED


def test_journey_timeline_builder_append_event_creates_new_timeline():
    builder = JourneyTimelineBuilder()
    j_id = uuid.uuid4()
    timeline1 = builder.create_initial_timeline(j_id, datetime.now(timezone.utc))

    event = JourneyTimelineEvent(
        event_id=uuid.uuid4(),
        journey_instance_id=j_id,
        event_type=TimelineEventType.STAGE_ENTERED,
        timestamp=datetime.now(timezone.utc),
        metadata={"description": "Transition"},
    )
    timeline2 = builder.append_event(timeline1, event)

    assert timeline1 is not timeline2
    assert len(timeline1.events) == 1
    assert len(timeline2.events) == 2


def test_timeline_events_are_chronologically_ordered():
    builder = JourneyTimelineBuilder()
    j_id = uuid.uuid4()
    t1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2023, 1, 2, tzinfo=timezone.utc)

    timeline = builder.create_initial_timeline(j_id, t1)
    event = JourneyTimelineEvent(
        event_id=uuid.uuid4(),
        journey_instance_id=j_id,
        event_type=TimelineEventType.STAGE_ENTERED,
        timestamp=t2,
        metadata={"description": "Transition"},
    )
    timeline = builder.append_event(timeline, event)

    assert timeline.events[0].timestamp < timeline.events[1].timestamp


def test_timeline_preserves_all_historical_events():
    builder = JourneyTimelineBuilder()
    j_id = uuid.uuid4()
    timeline = builder.create_initial_timeline(j_id, datetime.now(timezone.utc))
    event = JourneyTimelineEvent(
        event_id=uuid.uuid4(),
        journey_instance_id=j_id,
        event_type=TimelineEventType.STAGE_ENTERED,
        timestamp=datetime.now(timezone.utc),
        metadata={"description": "Transition"},
    )
    timeline = builder.append_event(timeline, event)
    assert len(timeline.events) == 2
