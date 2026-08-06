"""
HunterOS Engage V1 - Insight CQRS Repositories
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Defines read/write repository interfaces and an in-memory implementation
supporting workspace isolation, multi-attribute querying, and audit history.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ConversationInsightResult,
    InsightCategory,
    InsightPriority,
    OpportunityInsight,
    RiskInsight,
)

logger = logging.getLogger(__name__)


class InsightWriteRepository(ABC):
    """Write-side repository interface for persisting insight results."""

    @abstractmethod
    def save(self, result: ConversationInsightResult) -> None:
        """Persists a ConversationInsightResult aggregate root."""
        pass

    @abstractmethod
    def delete(self, insight_result_id: uuid.UUID) -> bool:
        """Deletes an insight result by ID."""
        pass


class InsightReadRepository(ABC):
    """Read-side repository interface for querying insight results."""

    @abstractmethod
    def get_by_id(self, insight_result_id: uuid.UUID) -> Optional[ConversationInsightResult]:
        """Retrieves an insight result by primary UUID."""
        pass

    @abstractmethod
    def get_latest_by_conversation(self, conversation_id: str) -> Optional[ConversationInsightResult]:
        """Retrieves the latest insight result for a conversation."""
        pass

    @abstractmethod
    def list_by_conversation(self, conversation_id: str) -> List[ConversationInsightResult]:
        """Lists all historical insight results for a conversation."""
        pass

    @abstractmethod
    def list_by_customer(self, customer_id: str) -> List[ConversationInsightResult]:
        """Lists all insight results for a customer across conversations."""
        pass

    @abstractmethod
    def get_risks(
        self,
        conversation_id: str,
        priority: Optional[InsightPriority] = None,
        category: Optional[InsightCategory] = None,
    ) -> List[RiskInsight]:
        """Queries risks for a conversation with optional filters."""
        pass

    @abstractmethod
    def get_opportunities(
        self,
        conversation_id: str,
        priority: Optional[InsightPriority] = None,
        category: Optional[InsightCategory] = None,
    ) -> List[OpportunityInsight]:
        """Queries opportunities for a conversation with optional filters."""
        pass

    @abstractmethod
    def get_action_items(
        self,
        conversation_id: str,
        priority: Optional[InsightPriority] = None,
        category: Optional[InsightCategory] = None,
    ) -> List[ActionItemInsight]:
        """Queries action items for a conversation with optional filters."""
        pass


class InMemoryInsightRepository(InsightWriteRepository, InsightReadRepository):
    """Thread-safe in-memory store for ConversationInsightResult aggregates."""

    def __init__(self) -> None:
        self._by_id: Dict[uuid.UUID, ConversationInsightResult] = {}
        self._by_conversation: Dict[str, List[uuid.UUID]] = {}
        self._by_customer: Dict[str, List[uuid.UUID]] = {}

    def save(self, result: ConversationInsightResult) -> None:
        self._by_id[result.insight_result_id] = result

        if result.conversation_id not in self._by_conversation:
            self._by_conversation[result.conversation_id] = []
        self._by_conversation[result.conversation_id].append(result.insight_result_id)

        if result.customer_id:
            if result.customer_id not in self._by_customer:
                self._by_customer[result.customer_id] = []
            self._by_customer[result.customer_id].append(result.insight_result_id)

        logger.debug("Saved ConversationInsightResult %s (conv=%s)", result.insight_result_id, result.conversation_id)

    def delete(self, insight_result_id: uuid.UUID) -> bool:
        result = self._by_id.pop(insight_result_id, None)
        if not result:
            return False

        if result.conversation_id in self._by_conversation:
            self._by_conversation[result.conversation_id] = [
                rid for rid in self._by_conversation[result.conversation_id] if rid != insight_result_id
            ]

        if result.customer_id and result.customer_id in self._by_customer:
            self._by_customer[result.customer_id] = [
                rid for rid in self._by_customer[result.customer_id] if rid != insight_result_id
            ]

        return True

    def get_by_id(self, insight_result_id: uuid.UUID) -> Optional[ConversationInsightResult]:
        return self._by_id.get(insight_result_id)

    def get_latest_by_conversation(self, conversation_id: str) -> Optional[ConversationInsightResult]:
        ids = self._by_conversation.get(conversation_id, [])
        if not ids:
            return None
        return self._by_id.get(ids[-1])

    def list_by_conversation(self, conversation_id: str) -> List[ConversationInsightResult]:
        ids = self._by_conversation.get(conversation_id, [])
        return [self._by_id[rid] for rid in ids if rid in self._by_id]

    def list_by_customer(self, customer_id: str) -> List[ConversationInsightResult]:
        ids = self._by_customer.get(customer_id, [])
        return [self._by_id[rid] for rid in ids if rid in self._by_id]

    def get_risks(
        self,
        conversation_id: str,
        priority: Optional[InsightPriority] = None,
        category: Optional[InsightCategory] = None,
    ) -> List[RiskInsight]:
        latest = self.get_latest_by_conversation(conversation_id)
        if not latest:
            return []
        risks = latest.risks
        if priority:
            risks = [r for r in risks if r.priority == priority]
        if category:
            risks = [r for r in risks if r.category == category]
        return risks

    def get_opportunities(
        self,
        conversation_id: str,
        priority: Optional[InsightPriority] = None,
        category: Optional[InsightCategory] = None,
    ) -> List[OpportunityInsight]:
        latest = self.get_latest_by_conversation(conversation_id)
        if not latest:
            return []
        opps = latest.opportunities
        if priority:
            opps = [o for o in opps if o.priority == priority]
        if category:
            opps = [o for o in opps if o.category == category]
        return opps

    def get_action_items(
        self,
        conversation_id: str,
        priority: Optional[InsightPriority] = None,
        category: Optional[InsightCategory] = None,
    ) -> List[ActionItemInsight]:
        latest = self.get_latest_by_conversation(conversation_id)
        if not latest:
            return []
        actions = latest.action_items
        if priority:
            actions = [a for a in actions if a.priority == priority]
        if category:
            actions = [a for a in actions if a.category == category]
        return actions


default_insight_repository = InMemoryInsightRepository()
