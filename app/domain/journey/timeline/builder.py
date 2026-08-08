from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from app.domain.journey.models import (
    JourneyEvidence,
    JourneyStageTransition,
    JourneyState,
    JourneyTimeline,
    JourneyTimelineEvent,
    TimelineEventType,
    TransitionType,
)
from app.domain.journey.timeline.models import JourneyTimelineView


class JourneyTimelineBuilder:
    """Builder for journey timelines and timeline events."""

    def create_initial_timeline(
        self,
        journey_instance_id: Union[uuid.UUID, str],
        timestamp: Optional[datetime] = None,
        workspace_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> JourneyTimeline:
        """Create a new timeline initialized with a JOURNEY_STARTED event."""
        j_id = journey_instance_id if isinstance(journey_instance_id, uuid.UUID) else uuid.UUID(str(journey_instance_id))
        ts = timestamp or datetime.now(timezone.utc)
        start_event = JourneyTimelineEvent(
            event_id=uuid.uuid4(),
            journey_instance_id=j_id,
            workspace_id=workspace_id,
            event_type=TimelineEventType.JOURNEY_STARTED,
            timestamp=ts,
            metadata={"description": "Journey initiated"},
        )
        return JourneyTimeline(
            timeline_id=uuid.uuid4(),
            journey_instance_id=j_id,
            workspace_id=workspace_id,
            events=[start_event],
        )

    def create_journey_started_event(
        self,
        journey_state: JourneyState,
        evidence: Optional[List[JourneyEvidence]] = None,
    ) -> JourneyTimelineEvent:
        """Create a timeline event for the start of a journey."""
        return JourneyTimelineEvent(
            event_id=uuid.uuid4(),
            journey_instance_id=journey_state.journey_instance_id,
            workspace_id=journey_state.workspace_id,
            event_type=TimelineEventType.JOURNEY_STARTED,
            stage=journey_state.current_stage,
            timestamp=datetime.now(timezone.utc),
            evidence=evidence or [],
            metadata={"description": f"Journey started at stage {journey_state.current_stage.value}"},
        )

    def create_stage_transition_event(
        self,
        transition: JourneyStageTransition,
        journey_state: JourneyState,
    ) -> JourneyTimelineEvent:
        """Create a timeline event from a stage transition."""
        event_type_mapping = {
            TransitionType.ADVANCE: TimelineEventType.STAGE_ADVANCED,
            TransitionType.REGRESSION: TimelineEventType.STAGE_REGRESSED,
            TransitionType.REACTIVATION: TimelineEventType.STAGE_REACTIVATED,
            TransitionType.COMPLETION: TimelineEventType.STAGE_COMPLETED,
            TransitionType.CLOSURE: TimelineEventType.JOURNEY_CLOSED,
            TransitionType.INITIALIZATION: TimelineEventType.STAGE_ENTERED,
        }
        event_type = event_type_mapping.get(transition.transition_type, TimelineEventType.STAGE_ENTERED)

        return JourneyTimelineEvent(
            event_id=uuid.uuid4(),
            journey_instance_id=journey_state.journey_instance_id,
            workspace_id=journey_state.workspace_id,
            event_type=event_type,
            stage=transition.to_stage,
            previous_stage=transition.from_stage,
            timestamp=transition.occurred_at,
            evidence=transition.evidence,
            confidence=transition.confidence,
            metadata={
                "reason": transition.reason,
                "transition_id": str(transition.transition_id),
            },
        )

    def create_no_change_event(self, journey_state: JourneyState) -> JourneyTimelineEvent:
        """Create a timeline event indicating no stage change."""
        return JourneyTimelineEvent(
            event_id=uuid.uuid4(),
            journey_instance_id=journey_state.journey_instance_id,
            workspace_id=journey_state.workspace_id,
            event_type=TimelineEventType.NO_CHANGE_OBSERVATION,
            stage=journey_state.current_stage,
            timestamp=datetime.now(timezone.utc),
            evidence=[],
            metadata={"description": "Journey evaluated with no stage change"},
        )

    def append_event(self, timeline: JourneyTimeline, event: JourneyTimelineEvent) -> JourneyTimeline:
        """Return a new timeline with the event appended."""
        new_events = list(timeline.events) + [event]
        return JourneyTimeline(
            timeline_id=timeline.timeline_id,
            journey_instance_id=timeline.journey_instance_id,
            workspace_id=timeline.workspace_id,
            events=new_events,
        )

    def build_timeline_view(self, timeline: JourneyTimeline) -> JourneyTimelineView:
        """Compute durations between stage entries and build a view."""
        events = sorted(timeline.events, key=lambda x: x.timestamp)
        total_events = len(events)

        if not events:
            return JourneyTimelineView(
                timeline=timeline,
                total_events=0,
                first_event_at=None,
                last_event_at=None,
                stage_durations={},
            )

        first_event_at = events[0].timestamp
        last_event_at = events[-1].timestamp

        stage_durations: Dict[str, float] = {}
        current_stage = None
        stage_entry_time = None

        for event in events:
            if event.stage:
                if current_stage and stage_entry_time:
                    duration = (event.timestamp - stage_entry_time).total_seconds()
                    stage_durations[current_stage] = stage_durations.get(current_stage, 0.0) + duration

                current_stage = event.stage.value if hasattr(event.stage, "value") else str(event.stage)
                stage_entry_time = event.timestamp

        if current_stage and stage_entry_time:
            duration = (last_event_at - stage_entry_time).total_seconds()
            stage_durations[current_stage] = stage_durations.get(current_stage, 0.0) + duration

        return JourneyTimelineView(
            timeline=timeline,
            total_events=total_events,
            first_event_at=first_event_at,
            last_event_at=last_event_at,
            stage_durations=stage_durations,
        )
