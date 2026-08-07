"""
HunterOS Engage V1 - Resolution Repository
Thread-safe repository for persisting and retrieving MultiIntentResolutionResult entities.
"""

from __future__ import annotations

from collections import defaultdict
import threading
from typing import Dict, List, Optional, Tuple
import uuid

from app.domain.intents.resolution.models import MultiIntentResolutionResult


class ResolutionRepository:
    """
    Thread-safe repository for MultiIntentResolutionResult aggregate roots.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._by_id: Dict[uuid.UUID, MultiIntentResolutionResult] = {}
        self._by_entity: Dict[Tuple[str, str], List[uuid.UUID]] = defaultdict(list)
        self._by_conversation: Dict[str, uuid.UUID] = {}
        self._by_workspace: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)

    def save(self, result: MultiIntentResolutionResult) -> MultiIntentResolutionResult:
        """Store or overwrite a resolution result."""
        with self._lock:
            self._by_id[result.resolution_id] = result
            entity_key = (result.entity_type, result.entity_id)
            if result.resolution_id not in self._by_entity[entity_key]:
                self._by_entity[entity_key].append(result.resolution_id)

            self._by_conversation[result.conversation_id] = result.resolution_id

            if result.workspace_id:
                if result.resolution_id not in self._by_workspace[result.workspace_id]:
                    self._by_workspace[result.workspace_id].append(result.resolution_id)

            return result

    def get_by_id(self, resolution_id: uuid.UUID) -> Optional[MultiIntentResolutionResult]:
        with self._lock:
            return self._by_id.get(resolution_id)

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> List[MultiIntentResolutionResult]:
        with self._lock:
            res_ids = self._by_entity.get((entity_type, entity_id), [])
            results = [self._by_id[rid] for rid in res_ids if rid in self._by_id]
            if workspace_id:
                results = [r for r in results if r.workspace_id == workspace_id]
            return sorted(results, key=lambda r: r.generated_at, reverse=True)

    def get_latest_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Optional[MultiIntentResolutionResult]:
        results = self.get_by_entity(entity_type, entity_id, workspace_id)
        return results[0] if results else None

    def get_by_conversation(self, conversation_id: str) -> Optional[MultiIntentResolutionResult]:
        with self._lock:
            rid = self._by_conversation.get(conversation_id)
            return self._by_id.get(rid) if rid else None

    def list_all(self, workspace_id: Optional[uuid.UUID] = None) -> List[MultiIntentResolutionResult]:
        with self._lock:
            results = list(self._by_id.values())
            if workspace_id:
                results = [r for r in results if r.workspace_id == workspace_id]
            return sorted(results, key=lambda r: r.generated_at, reverse=True)

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_entity.clear()
            self._by_conversation.clear()
            self._by_workspace.clear()


# Default singleton instance
default_resolution_repository = ResolutionRepository()
