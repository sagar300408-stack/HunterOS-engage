"""
HunterOS Engage V1 - Intent Domain Repositories
CQRS Read and Write storage abstraction for Intent Intelligence.
"""

from __future__ import annotations

import abc
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionResult,
    IntentTaxonomyCategory,
    IntentType,
)


class IntentRepository(abc.ABC):
    """Abstract base repository for Intent Detection results."""

    @abc.abstractmethod
    def save(self, result: IntentDetectionResult) -> None:
        pass

    @abc.abstractmethod
    def get_by_conversation_id(self, conversation_id: str) -> Optional[IntentDetectionResult]:
        pass

    @abc.abstractmethod
    def get_by_detection_id(self, detection_id: uuid.UUID) -> Optional[IntentDetectionResult]:
        pass

    @abc.abstractmethod
    def query_intents(
        self,
        conversation_id: Optional[str] = None,
        workspace_id: Optional[uuid.UUID] = None,
        intent_type: Optional[IntentType] = None,
        category: Optional[IntentTaxonomyCategory] = None,
        importance: Optional[BusinessImportance] = None,
        min_confidence: float = 0.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[DetectedIntent]:
        pass

    @abc.abstractmethod
    def delete_by_conversation_id(self, conversation_id: str) -> bool:
        pass


class InMemoryIntentRepository(IntentRepository):
    """Thread-safe in-memory store for Intent Intelligence."""

    def __init__(self):
        self._lock = threading.RLock()
        self._by_conversation: Dict[str, IntentDetectionResult] = {}
        self._by_detection_id: Dict[uuid.UUID, IntentDetectionResult] = {}

    def save(self, result: IntentDetectionResult) -> None:
        with self._lock:
            self._by_conversation[result.conversation_id] = result
            self._by_detection_id[result.detection_id] = result

    def get_by_conversation_id(self, conversation_id: str) -> Optional[IntentDetectionResult]:
        with self._lock:
            return self._by_conversation.get(conversation_id)

    def get_by_detection_id(self, detection_id: uuid.UUID) -> Optional[IntentDetectionResult]:
        with self._lock:
            return self._by_detection_id.get(detection_id)

    def query_intents(
        self,
        conversation_id: Optional[str] = None,
        workspace_id: Optional[uuid.UUID] = None,
        intent_type: Optional[IntentType] = None,
        category: Optional[IntentTaxonomyCategory] = None,
        importance: Optional[BusinessImportance] = None,
        min_confidence: float = 0.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[DetectedIntent]:
        with self._lock:
            matches: List[DetectedIntent] = []

            results = (
                [self._by_conversation[conversation_id]]
                if conversation_id and conversation_id in self._by_conversation
                else list(self._by_conversation.values())
            )

            for res in results:
                if workspace_id and res.workspace_id != workspace_id:
                    continue

                for intent in res.intents:
                    if intent_type:
                        t_str = intent_type.value if hasattr(intent_type, "value") else str(intent_type)
                        i_t_str = intent.intent_type.value if hasattr(intent.intent_type, "value") else str(intent.intent_type)
                        if i_t_str.upper() != t_str.upper():
                            continue
                    if category:
                        cat_str = category.value if hasattr(category, "value") else str(category)
                        intent_cat_str = intent.taxonomy_category.value if hasattr(intent.taxonomy_category, "value") else str(intent.taxonomy_category)
                        if intent_cat_str.lower() != cat_str.lower():
                            continue
                    if importance:
                        imp_str = importance.value if hasattr(importance, "value") else str(importance)
                        i_imp_str = intent.business_importance.value if hasattr(intent.business_importance, "value") else str(intent.business_importance)
                        if i_imp_str.upper() != imp_str.upper():
                            continue
                    if intent.confidence < min_confidence:
                        continue
                    if start_date and intent.detected_at < start_date:
                        continue
                    if end_date and intent.detected_at > end_date:
                        continue

                    matches.append(intent)
                    if len(matches) >= limit:
                        return matches

            return matches

    def delete_by_conversation_id(self, conversation_id: str) -> bool:
        with self._lock:
            result = self._by_conversation.pop(conversation_id, None)
            if result:
                self._by_detection_id.pop(result.detection_id, None)
                return True
            return False


# Default singleton instance
default_intent_repository = InMemoryIntentRepository()
