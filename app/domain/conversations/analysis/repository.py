"""
HunterOS Engage — CQRS Conversation Analysis Repositories (Phase 2.2.1)

Enforces CQRS separation for Conversation Analysis data access:
- ConversationAnalysisReadRepository: Query operations only
- ConversationAnalysisWriteRepository: Persistence and deletion operations only
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.domain.conversations.analysis.models import (
    ConversationAnalysisResult,
    ConversationMetadata,
    ConversationSegment,
    ConversationSummary,
    ExtractedFact,
    FactCategory,
    TopicAnalysis,
)


# ── Read Repository (Query Side) ──────────────────────────────────────────────

class AbstractConversationAnalysisReadRepository(ABC):
    """Read-only query repository contract for Conversation Analysis."""

    @abstractmethod
    def get_by_id(self, analysis_id: uuid.UUID) -> Optional[ConversationAnalysisResult]:
        """Fetch analysis aggregate by analysis ID."""
        pass

    @abstractmethod
    def get_by_conversation_id(self, conversation_id: str) -> Optional[ConversationAnalysisResult]:
        """Fetch latest analysis aggregate by conversation ID."""
        pass

    @abstractmethod
    def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ConversationAnalysisResult]:
        """List analysis records for a given workspace."""
        pass

    @abstractmethod
    def get_topics(self, conversation_id: str) -> Optional[TopicAnalysis]:
        """Fetch topic analysis projection for a conversation."""
        pass

    @abstractmethod
    def get_facts(
        self,
        conversation_id: str,
        category: Optional[FactCategory] = None,
    ) -> List[ExtractedFact]:
        """Fetch extracted facts projection, optionally filtered by category."""
        pass

    @abstractmethod
    def get_summaries(self, conversation_id: str) -> Dict[str, ConversationSummary]:
        """Fetch summary projections for a conversation."""
        pass

    @abstractmethod
    def get_segments(self, conversation_id: str) -> List[ConversationSegment]:
        """Fetch segment projections for a conversation."""
        pass

    @abstractmethod
    def get_metadata(self, conversation_id: str) -> Optional[ConversationMetadata]:
        """Fetch structural metadata for a conversation."""
        pass


# ── Write Repository (Command Side) ───────────────────────────────────────────

class AbstractConversationAnalysisWriteRepository(ABC):
    """Write-only command repository contract for Conversation Analysis."""

    @abstractmethod
    def save(self, result: ConversationAnalysisResult) -> None:
        """Persist a conversation analysis aggregate."""
        pass

    @abstractmethod
    def delete(self, analysis_id: uuid.UUID) -> bool:
        """Remove an analysis aggregate by analysis ID."""
        pass

    @abstractmethod
    def delete_by_conversation_id(self, conversation_id: str) -> bool:
        """Remove all analysis aggregates for a given conversation ID."""
        pass


# ── In-Memory CQRS Implementations ────────────────────────────────────────────

class InMemoryConversationAnalysisStorage:
    """Shared underlying memory store for in-memory read & write repositories."""

    def __init__(self) -> None:
        self.by_id: Dict[uuid.UUID, ConversationAnalysisResult] = {}
        self.by_conv_id: Dict[str, uuid.UUID] = {}


class InMemoryConversationAnalysisReadRepository(AbstractConversationAnalysisReadRepository):
    """In-memory implementation of Read Repository."""

    def __init__(self, storage: Optional[InMemoryConversationAnalysisStorage] = None) -> None:
        self._storage = storage or InMemoryConversationAnalysisStorage()

    @property
    def storage(self) -> InMemoryConversationAnalysisStorage:
        return self._storage

    def get_by_id(self, analysis_id: uuid.UUID) -> Optional[ConversationAnalysisResult]:
        return self._storage.by_id.get(analysis_id)

    def get_by_conversation_id(self, conversation_id: str) -> Optional[ConversationAnalysisResult]:
        aid = self._storage.by_conv_id.get(conversation_id)
        if aid:
            return self._storage.by_id.get(aid)
        return None

    def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ConversationAnalysisResult]:
        matches = [
            res for res in self._storage.by_id.values()
            if res.workspace_id == workspace_id
        ]
        return matches[offset : offset + limit]

    def get_topics(self, conversation_id: str) -> Optional[TopicAnalysis]:
        res = self.get_by_conversation_id(conversation_id)
        return res.topics if res else None

    def get_facts(
        self,
        conversation_id: str,
        category: Optional[FactCategory] = None,
    ) -> List[ExtractedFact]:
        res = self.get_by_conversation_id(conversation_id)
        if not res:
            return []
        if category:
            return [f for f in res.facts if f.category == category]
        return res.facts

    def get_summaries(self, conversation_id: str) -> Dict[str, ConversationSummary]:
        res = self.get_by_conversation_id(conversation_id)
        return res.summaries if res else {}

    def get_segments(self, conversation_id: str) -> List[ConversationSegment]:
        res = self.get_by_conversation_id(conversation_id)
        return res.segments if res else []

    def get_metadata(self, conversation_id: str) -> Optional[ConversationMetadata]:
        res = self.get_by_conversation_id(conversation_id)
        return res.metadata if res else None


class InMemoryConversationAnalysisWriteRepository(AbstractConversationAnalysisWriteRepository):
    """In-memory implementation of Write Repository."""

    def __init__(self, storage: Optional[InMemoryConversationAnalysisStorage] = None) -> None:
        self._storage = storage or InMemoryConversationAnalysisStorage()

    @property
    def storage(self) -> InMemoryConversationAnalysisStorage:
        return self._storage

    def save(self, result: ConversationAnalysisResult) -> None:
        self._storage.by_id[result.analysis_id] = result
        self._storage.by_conv_id[result.conversation_id] = result.analysis_id

    def delete(self, analysis_id: uuid.UUID) -> bool:
        if analysis_id in self._storage.by_id:
            res = self._storage.by_id.pop(analysis_id)
            if res.conversation_id in self._storage.by_conv_id:
                del self._storage.by_conv_id[res.conversation_id]
            return True
        return False

    def delete_by_conversation_id(self, conversation_id: str) -> bool:
        aid = self._storage.by_conv_id.pop(conversation_id, None)
        if aid and aid in self._storage.by_id:
            del self._storage.by_id[aid]
            return True
        return False
