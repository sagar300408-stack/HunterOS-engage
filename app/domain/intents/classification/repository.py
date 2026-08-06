"""
HunterOS Engage V1 - Intent Classification Repository
Thread-safe in-memory CQRS repository with multi-attribute secondary indexing.
"""

from __future__ import annotations

from collections import defaultdict
import threading
from typing import Dict, List, Optional, Set
import uuid

from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
    IntentClassificationResult,
)


class InMemoryIntentClassificationRepository:
    """
    Thread-safe repository for IntentClassificationResult aggregate roots.
    Maintains primary key and secondary index lookups.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._storage: Dict[uuid.UUID, IntentClassificationResult] = {}
        # Secondary indices
        self._by_conversation: Dict[str, List[uuid.UUID]] = defaultdict(list)
        self._by_workspace: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
        self._by_category: Dict[IntentCategory, List[uuid.UUID]] = defaultdict(list)
        self._by_domain: Dict[BusinessDomain, List[uuid.UUID]] = defaultdict(list)

    def save(self, result: IntentClassificationResult) -> IntentClassificationResult:
        """Store or update classification result and refresh indexes."""
        with self._lock:
            cid = result.classification_id
            self._storage[cid] = result

            if cid not in self._by_conversation[result.conversation_id]:
                self._by_conversation[result.conversation_id].append(cid)

            if result.workspace_id:
                if cid not in self._by_workspace[result.workspace_id]:
                    self._by_workspace[result.workspace_id].append(cid)

            for intent in result.classified_intents:
                if cid not in self._by_category[intent.business_category]:
                    self._by_category[intent.business_category].append(cid)
                if cid not in self._by_domain[intent.business_domain]:
                    self._by_domain[intent.business_domain].append(cid)

            return result

    def get_by_id(self, classification_id: uuid.UUID) -> Optional[IntentClassificationResult]:
        """Fetch result by UUID."""
        with self._lock:
            return self._storage.get(classification_id)

    def get_by_conversation_id(self, conversation_id: str) -> List[IntentClassificationResult]:
        """Fetch all results for a conversation."""
        with self._lock:
            cids = self._by_conversation.get(conversation_id, [])
            return [self._storage[cid] for cid in cids if cid in self._storage]

    def get_latest_by_conversation_id(self, conversation_id: str) -> Optional[IntentClassificationResult]:
        """Fetch latest classification result for a conversation."""
        results = self.get_by_conversation_id(conversation_id)
        if not results:
            return None
        return max(results, key=lambda r: r.metadata.created_at)

    def list_by_workspace(self, workspace_id: uuid.UUID) -> List[IntentClassificationResult]:
        """Fetch all results belonging to a workspace."""
        with self._lock:
            cids = self._by_workspace.get(workspace_id, [])
            return [self._storage[cid] for cid in cids if cid in self._storage]

    def list_all(self) -> List[IntentClassificationResult]:
        """Return all stored results."""
        with self._lock:
            return list(self._storage.values())

    def count(self) -> int:
        """Return count of stored results."""
        with self._lock:
            return len(self._storage)

    def clear(self) -> None:
        """Clear all stored data (useful for test isolation)."""
        with self._lock:
            self._storage.clear()
            self._by_conversation.clear()
            self._by_workspace.clear()
            self._by_category.clear()
            self._by_domain.clear()


default_classification_repository = InMemoryIntentClassificationRepository()
