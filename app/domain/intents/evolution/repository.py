"""
HunterOS Engage V1 - Intent Evolution Repository (CQRS)
Thread-safe in-memory store for evolution results, event streams, snapshots, and histories.
"""

from __future__ import annotations

from datetime import datetime
import threading
from typing import Dict, List, Optional, Tuple
import uuid

from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEvent,
    IntentEvolutionEventStream,
    IntentEvolutionResult,
    IntentHistory,
    IntentStateSnapshot,
    IntentTimeline,
)


class IntentEvolutionRepository:
    """
    Thread-safe CQRS repository storing event streams and evolution aggregates.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._results: Dict[uuid.UUID, IntentEvolutionResult] = {}
        # Key: (entity_type.value, entity_id, str(workspace_id) if workspace_id else "")
        self._streams: Dict[Tuple[str, str, str], IntentEvolutionEventStream] = {}
        self._snapshots: Dict[Tuple[str, str, str], List[IntentStateSnapshot]] = {}
        self._histories: Dict[uuid.UUID, IntentHistory] = {}
        self._timelines: Dict[uuid.UUID, IntentTimeline] = {}

    def _entity_key(
        self,
        entity_type: EntityType,
        entity_id: str,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Tuple[str, str, str]:
        return (entity_type.value, entity_id, str(workspace_id) if workspace_id else "")

    def save_evolution_result(self, result: IntentEvolutionResult) -> None:
        """Persist a complete evolution result aggregate and update indexed collections."""
        with self._lock:
            self._results[result.evolution_id] = result
            k = self._entity_key(result.entity_type, result.entity_id, result.workspace_id)
            self._streams[k] = result.event_stream

            for h in result.intent_histories:
                self._histories[h.intent_id] = h

            for t in result.timelines:
                self._timelines[t.intent_id] = t

    def save_snapshot(self, snapshot: IntentStateSnapshot) -> None:
        """Persist an individual intent state snapshot."""
        with self._lock:
            k = self._entity_key(snapshot.entity_type, snapshot.entity_id, snapshot.workspace_id)
            self._snapshots.setdefault(k, []).append(snapshot)

    def get_evolution_result(self, evolution_id: uuid.UUID) -> Optional[IntentEvolutionResult]:
        """Fetch evolution result by ID."""
        with self._lock:
            return self._results.get(evolution_id)

    def get_latest_result_for_entity(
        self,
        entity_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Optional[IntentEvolutionResult]:
        """Fetch latest evolution result for an entity."""
        with self._lock:
            matching = [
                r
                for r in self._results.values()
                if r.entity_id == entity_id
                and r.entity_type == entity_type
                and (workspace_id is None or r.workspace_id == workspace_id)
            ]
            if not matching:
                return None
            return sorted(matching, key=lambda x: x.generated_at)[-1]

    def get_event_stream(
        self,
        entity_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Optional[IntentEvolutionEventStream]:
        """Fetch the current immutable event stream for an entity."""
        with self._lock:
            k = self._entity_key(entity_type, entity_id, workspace_id)
            return self._streams.get(k)

    def get_snapshots(
        self,
        entity_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> List[IntentStateSnapshot]:
        """Fetch all historical snapshots recorded for an entity."""
        with self._lock:
            k = self._entity_key(entity_type, entity_id, workspace_id)
            return list(self._snapshots.get(k, []))

    def get_history(self, intent_id: uuid.UUID) -> Optional[IntentHistory]:
        """Fetch history for a specific intent ID."""
        with self._lock:
            return self._histories.get(intent_id)

    def get_timeline(self, intent_id: uuid.UUID) -> Optional[IntentTimeline]:
        """Fetch timeline for a specific intent ID."""
        with self._lock:
            return self._timelines.get(intent_id)

    def clear(self) -> None:
        """Clear all stored state (testing support)."""
        with self._lock:
            self._results.clear()
            self._streams.clear()
            self._snapshots.clear()
            self._histories.clear()
            self._timelines.clear()


default_evolution_repository = IntentEvolutionRepository()
