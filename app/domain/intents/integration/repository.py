"""
HunterOS Engage V1 - Intent Context Repository
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Thread-safe in-memory repository for storing and querying IntentIntelligenceContext aggregates.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional
import uuid

from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext

logger = logging.getLogger(__name__)


class IntentContextRepository:
    """Thread-safe in-memory repository for Intent Intelligence Contexts."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._contexts: Dict[uuid.UUID, IntentIntelligenceContext] = {}
        self._conversation_index: Dict[str, List[uuid.UUID]] = {}
        self._entity_index: Dict[str, List[uuid.UUID]] = {}
        self._workspace_index: Dict[str, List[uuid.UUID]] = {}

    def save(self, context: IntentIntelligenceContext) -> IntentIntelligenceContext:
        with self._lock:
            cid = context.context_id
            self._contexts[cid] = context

            # Update indices
            if context.conversation_id not in self._conversation_index:
                self._conversation_index[context.conversation_id] = []
            if cid not in self._conversation_index[context.conversation_id]:
                self._conversation_index[context.conversation_id].append(cid)

            if context.entity_id not in self._entity_index:
                self._entity_index[context.entity_id] = []
            if cid not in self._entity_index[context.entity_id]:
                self._entity_index[context.entity_id].append(cid)

            if context.workspace_id not in self._workspace_index:
                self._workspace_index[context.workspace_id] = []
            if cid not in self._workspace_index[context.workspace_id]:
                self._workspace_index[context.workspace_id].append(cid)

            logger.debug("Saved IntentIntelligenceContext %s (conv=%s)", cid, context.conversation_id)
            return context

    def get_by_id(self, context_id: uuid.UUID) -> Optional[IntentIntelligenceContext]:
        with self._lock:
            return self._contexts.get(context_id)

    def get_by_conversation(
        self,
        conversation_id: str,
        profile: Optional[CompositionProfileType] = None,
    ) -> Optional[IntentIntelligenceContext]:
        with self._lock:
            cids = self._conversation_index.get(conversation_id, [])
            if not cids:
                return None

            # Look for matching profile or return most recently saved context
            for cid in reversed(cids):
                ctx = self._contexts.get(cid)
                if ctx:
                    if profile is None:
                        return ctx
                    req_prof = profile.value if hasattr(profile, "value") else str(profile)
                    if ctx.metadata.composition_profile.upper() == req_prof.upper():
                        return ctx

            # Fallback to latest
            latest_id = cids[-1]
            return self._contexts.get(latest_id)

    def query(
        self,
        workspace_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        profile: Optional[CompositionProfileType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IntentIntelligenceContext]:
        with self._lock:
            results: List[IntentIntelligenceContext] = []

            # Find candidate IDs
            candidate_ids: Optional[List[uuid.UUID]] = None

            if conversation_id:
                candidate_ids = self._conversation_index.get(conversation_id, [])
            elif entity_id:
                candidate_ids = self._entity_index.get(entity_id, [])
            elif workspace_id:
                candidate_ids = self._workspace_index.get(workspace_id, [])

            if candidate_ids is not None:
                candidates = [self._contexts[cid] for cid in candidate_ids if cid in self._contexts]
            else:
                candidates = list(self._contexts.values())

            # Filter candidates
            for ctx in candidates:
                if workspace_id and ctx.workspace_id != workspace_id:
                    continue
                if entity_id and ctx.entity_id != entity_id:
                    continue
                if conversation_id and ctx.conversation_id != conversation_id:
                    continue
                if profile:
                    req_prof = profile.value if hasattr(profile, "value") else str(profile)
                    if ctx.metadata.composition_profile.upper() != req_prof.upper():
                        continue
                results.append(ctx)

            # Sort descending by creation timestamp
            results.sort(key=lambda c: c.metadata.created_at, reverse=True)
            return results[offset : offset + limit]

    def delete_by_conversation(self, conversation_id: str) -> int:
        with self._lock:
            cids = self._conversation_index.pop(conversation_id, [])
            count = 0
            for cid in cids:
                if cid in self._contexts:
                    ctx = self._contexts.pop(cid)
                    # Clean other indices
                    if ctx.entity_id in self._entity_index:
                        self._entity_index[ctx.entity_id] = [
                            x for x in self._entity_index[ctx.entity_id] if x != cid
                        ]
                    if ctx.workspace_id in self._workspace_index:
                        self._workspace_index[ctx.workspace_id] = [
                            x for x in self._workspace_index[ctx.workspace_id] if x != cid
                        ]
                    count += 1
            return count

    def count(self) -> int:
        with self._lock:
            return len(self._contexts)


# Global default repository instance
default_context_repository = IntentContextRepository()
