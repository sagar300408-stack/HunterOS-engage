"""
HunterOS Engage V1 - Deal & Opportunity Intent Timeline Builder
Projects deal and commercial opportunity intent trajectories.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEvent,
    IntentLifecycleState,
    IntentStateSnapshot,
    IntentStateTransition,
    IntentTimeline,
    IntentVelocity,
)
from app.domain.intents.evolution.timelines.base import AbstractTimelineBuilder


class DealTimelineBuilder(AbstractTimelineBuilder):
    """
    Builds chronological intent timelines for Deal and Opportunity entities.
    """

    def __init__(self, entity_type: EntityType = EntityType.DEAL):
        super().__init__(entity_type=entity_type)

    def build_timeline(
        self,
        intent_id: uuid.UUID,
        entity_id: str,
        snapshots: List[IntentStateSnapshot],
        events: List[IntentEvolutionEvent],
        transitions: List[IntentStateTransition],
    ) -> IntentTimeline:
        sorted_snaps = sorted(snapshots, key=lambda s: s.observed_at)
        first_snap = sorted_snaps[0] if sorted_snaps else None
        last_snap = sorted_snaps[-1] if sorted_snaps else None

        now = datetime.now(timezone.utc)
        first_dt = first_snap.observed_at if first_snap else now
        last_dt = last_snap.observed_at if last_snap else now

        convs = list(dict.fromkeys(s.conversation_id for s in sorted_snaps if s.conversation_id))

        classification_hist = [
            {
                "observed_at": s.observed_at.isoformat(),
                "taxonomy_path": s.taxonomy_path,
                "category": s.category,
                "confidence": s.confidence,
                "conversation_id": s.conversation_id,
            }
            for s in sorted_snaps
        ]

        rel_hist = [
            {
                "observed_at": s.observed_at.isoformat(),
                "conversation_id": s.conversation_id,
                "relationships": s.relationships,
            }
            for s in sorted_snaps
            if s.relationships
        ]

        current_state = IntentLifecycleState.NEW
        if events:
            sorted_events = sorted(events, key=lambda e: e.occurred_at)
            current_state = sorted_events[-1].current_state
        elif len(sorted_snaps) > 1:
            current_state = IntentLifecycleState.PERSISTING

        velocity = self.calculate_velocity(sorted_snaps)
        current_confidence = last_snap.confidence if last_snap else 1.0
        intent_name = last_snap.intent_type if last_snap else "Unknown"
        taxonomy_path = last_snap.taxonomy_path if last_snap else "General"

        return IntentTimeline(
            intent_id=intent_id,
            entity_type=self.entity_type,
            entity_id=entity_id,
            intent_name=intent_name,
            taxonomy_path=taxonomy_path,
            first_detected_at=first_dt,
            last_observed_at=last_dt,
            observation_frequency=len(sorted_snaps),
            velocity=velocity,
            source_conversations=convs,
            state_transitions=sorted(transitions, key=lambda t: t.transitioned_at),
            classification_history=classification_hist,
            relationship_history=rel_hist,
            current_lifecycle_state=current_state,
            current_confidence=current_confidence,
            metadata={"deal_id": entity_id, "total_snapshots": len(sorted_snaps)},
        )
