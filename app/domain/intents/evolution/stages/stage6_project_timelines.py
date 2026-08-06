"""
HunterOS Engage V1 - Evolution Pipeline Stage 6: Project Timelines
Projects chronological timelines and history aggregates using the IntentTimelineRegistry.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import TYPE_CHECKING, Dict, List, Optional
import uuid

from app.domain.intents.evolution.models import (
    IntentHistory,
    IntentLifecycleState,
    IntentStateSnapshot,
    IntentTimeline,
)
from app.domain.intents.evolution.timelines.registry import (
    IntentTimelineRegistry,
    default_timeline_registry,
)

if TYPE_CHECKING:
    from app.domain.intents.evolution.context import IntentEvolutionContext


class ProjectTimelinesStage:
    """
    Stage 6: Reconstructs timeline projections and history aggregates from the event stream.
    """

    def __init__(self, timeline_registry: Optional[IntentTimelineRegistry] = None):
        self.timeline_registry = timeline_registry or default_timeline_registry

    def execute(self, context: IntentEvolutionContext) -> None:
        t0 = time.perf_counter()

        builder = self.timeline_registry.get_builder(context.entity_type)

        # Aggregate all snapshots (historical + current) by intent_id or taxonomy_path
        all_snaps: List[IntentStateSnapshot] = context.historical_snapshots + context.current_snapshots
        snaps_by_intent: Dict[uuid.UUID, List[IntentStateSnapshot]] = {}

        for s in all_snaps:
            snaps_by_intent.setdefault(s.intent_id, []).append(s)

        now = datetime.now(timezone.utc)

        for intent_id, snaps in snaps_by_intent.items():
            # Find associated events for this intent
            intent_events = [
                e for e in context.updated_stream.events if e.intent_id == intent_id
            ]

            # Build transitions list from events
            transitions = []
            # Sort events chronologically
            sorted_events = sorted(intent_events, key=lambda e: e.occurred_at)
            for ev in sorted_events:
                if ev.previous_state and ev.previous_state != ev.current_state:
                    from app.domain.intents.evolution.models import IntentStateTransition
                    transitions.append(
                        IntentStateTransition(
                            from_state=ev.previous_state,
                            to_state=ev.current_state,
                            transition_reason=f"Event {ev.event_type.value} occurred.",
                            transitioned_at=ev.occurred_at,
                            trigger_event_type=ev.event_type,
                        )
                    )

            timeline: IntentTimeline = builder.build_timeline(
                intent_id=intent_id,
                entity_id=context.entity_id,
                snapshots=snaps,
                events=intent_events,
                transitions=transitions,
            )
            context.projected_timelines[intent_id] = timeline

            # Build IntentHistory aggregate
            latest_snap = sorted(snaps, key=lambda s: s.observed_at)[-1]
            first_snap = sorted(snaps, key=lambda s: s.observed_at)[0]

            history = IntentHistory(
                intent_id=intent_id,
                entity_type=context.entity_type,
                entity_id=context.entity_id,
                workspace_id=context.workspace_id,
                canonical_intent_name=latest_snap.intent_type,
                current_state=timeline.current_lifecycle_state,
                timeline=timeline,
                snapshots=snaps,
                events=intent_events,
                created_at=first_snap.observed_at,
                updated_at=latest_snap.observed_at,
            )
            context.histories[intent_id] = history

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        context.record_stage_timing("Stage6_ProjectTimelines", elapsed_ms)
