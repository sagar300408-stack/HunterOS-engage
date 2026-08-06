"""
HunterOS Engage V1 - Intent Evolution Query Service & Descriptive Analytics
Provides read-side projections, event stream filtering, and descriptive analytics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEvent,
    IntentEvolutionEventType,
    IntentHistory,
    IntentLifecycleState,
    IntentTimeline,
    IntentVelocity,
)
from app.domain.intents.evolution.repository import (
    IntentEvolutionRepository,
    default_evolution_repository,
)


class IntentEvolutionQuery:
    """
    CQRS query service executing reads and descriptive analytics over intent evolution state.
    """

    def __init__(self, repository: Optional[IntentEvolutionRepository] = None):
        self.repository = repository or default_evolution_repository

    def get_history(self, intent_id: uuid.UUID) -> Optional[IntentHistory]:
        """Fetch complete multi-conversation history for an intent."""
        return self.repository.get_history(intent_id)

    def get_timeline(self, intent_id: uuid.UUID) -> Optional[IntentTimeline]:
        """Fetch chronological timeline projection for an intent."""
        return self.repository.get_timeline(intent_id)

    def get_current_intent_state(self, intent_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Fetch current lifecycle state and latest confidence for an intent."""
        t = self.repository.get_timeline(intent_id)
        if not t:
            return None
        return {
            "intent_id": str(t.intent_id),
            "intent_name": t.intent_name,
            "taxonomy_path": t.taxonomy_path,
            "current_lifecycle_state": t.current_lifecycle_state.value,
            "current_confidence": t.current_confidence,
            "velocity": t.velocity.value,
            "observation_frequency": t.observation_frequency,
            "last_observed_at": t.last_observed_at.isoformat(),
        }

    def get_entity_timelines(
        self,
        entity_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> List[IntentTimeline]:
        """Fetch all intent timelines for a specific entity."""
        latest_res = self.repository.get_latest_result_for_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            workspace_id=workspace_id,
        )
        if not latest_res:
            return []
        return list(latest_res.timelines)

    def get_events(
        self,
        entity_id: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
        workspace_id: Optional[uuid.UUID] = None,
        intent_id: Optional[uuid.UUID] = None,
        event_type: Optional[IntentEvolutionEventType] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[IntentEvolutionEvent]:
        """Query and filter immutable evolution events."""
        events: List[IntentEvolutionEvent] = []

        if entity_id:
            stream = self.repository.get_event_stream(
                entity_id=entity_id,
                entity_type=entity_type or EntityType.CUSTOMER,
                workspace_id=workspace_id,
            )
            if stream:
                events = list(stream.events)
        else:
            # Collect from all known results
            all_events = []
            for r in self.repository._results.values():
                if workspace_id is None or r.workspace_id == workspace_id:
                    all_events.extend(r.event_stream.events)
            events = all_events

        filtered: List[IntentEvolutionEvent] = []
        for e in events:
            if intent_id and e.intent_id != intent_id:
                continue
            if event_type and e.event_type != event_type:
                continue
            if from_date and e.occurred_at < from_date:
                continue
            if to_date and e.occurred_at > to_date:
                continue
            filtered.append(e)

        return sorted(filtered, key=lambda x: x.occurred_at)

    def get_analytics(
        self,
        entity_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Compute descriptive temporal analytics for an entity (historical only, zero forecasting).
        """
        stream = self.repository.get_event_stream(
            entity_id=entity_id,
            entity_type=entity_type,
            workspace_id=workspace_id,
        )
        events = stream.events if stream else []
        timelines = self.get_entity_timelines(entity_id, entity_type, workspace_id)

        state_dist: Dict[str, int] = {}
        for t in timelines:
            s_val = t.current_lifecycle_state.value
            state_dist[s_val] = state_dist.get(s_val, 0) + 1

        trans_dist: Dict[str, int] = {}
        for t in timelines:
            for tr in t.state_transitions:
                k = f"{tr.from_state.value}->{tr.to_state.value}"
                trans_dist[k] = trans_dist.get(k, 0) + 1

        merge_count = sum(1 for e in events if e.event_type == IntentEvolutionEventType.INTENT_MERGED)
        split_count = sum(1 for e in events if e.event_type == IntentEvolutionEventType.INTENT_SPLIT)

        # Lifecycle duration calculation
        duration_days = 0.0
        if timelines:
            min_dt = min(t.first_detected_at for t in timelines)
            max_dt = max(t.last_observed_at for t in timelines)
            duration_days = round(max((max_dt - min_dt).total_seconds() / 86400.0, 0.0), 2)

        # Evolution frequency (events per conversation)
        conv_ids = set()
        for e in events:
            conv_ids.update(e.source_conversations)
        total_convs = max(len(conv_ids), 1)
        evo_freq = round(len(events) / float(total_convs), 2)

        return {
            "entity_id": entity_id,
            "entity_type": entity_type.value,
            "workspace_id": str(workspace_id) if workspace_id else None,
            "total_evolutions": len(events),
            "evolution_frequency": evo_freq,
            "state_distribution": state_dist,
            "transition_distribution": trans_dist,
            "merge_count": merge_count,
            "split_count": split_count,
            "lifecycle_duration_days": duration_days,
            "average_velocity": timelines[0].velocity.value if timelines else IntentVelocity.UNKNOWN.value,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


default_evolution_query = IntentEvolutionQuery()
