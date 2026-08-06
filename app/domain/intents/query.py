"""
HunterOS Engage V1 - Intent Query Engine
CQRS Read-Side Query Engine for querying and projecting Intent Intelligence results.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionResult,
    IntentTaxonomyCategory,
    IntentType,
)
from app.domain.intents.repository import (
    IntentRepository,
    default_intent_repository,
)
from app.domain.intents.views.registry import (
    IntentViewRegistry,
    default_intent_view_registry,
)


class IntentQueryEngine:
    """Read-side CQRS query engine for Intent Intelligence."""

    def __init__(
        self,
        repository: Optional[IntentRepository] = None,
        view_registry: Optional[IntentViewRegistry] = None,
    ):
        self._repo = repository or default_intent_repository
        self._views = view_registry or default_intent_view_registry

    def get_conversation_intents(
        self, conversation_id: str
    ) -> Optional[IntentDetectionResult]:
        """Fetch the full intent detection aggregate for a conversation."""
        return self._repo.get_by_conversation_id(conversation_id)

    def get_intent_by_id(
        self, conversation_id: str, intent_id: uuid.UUID
    ) -> Optional[DetectedIntent]:
        """Fetch a specific detected intent by ID."""
        result = self._repo.get_by_conversation_id(conversation_id)
        if not result:
            return None
        for i in result.intents:
            if i.intent_id == intent_id:
                return i
        return None

    def query(
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
        """Query detected intents across multiple criteria."""
        return self._repo.query_intents(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            intent_type=intent_type,
            category=category,
            importance=importance,
            min_confidence=min_confidence,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    def render_view(
        self, conversation_id: str, view_name: str
    ) -> Optional[Dict[str, Any]]:
        """Render an intent view projection for a conversation."""
        result = self._repo.get_by_conversation_id(conversation_id)
        if not result:
            return None

        view = self._views.get_view(view_name)
        if not view:
            raise ValueError(f"Intent view '{view_name}' is not registered.")

        return view.render(result)


# Default singleton instance
default_intent_query_engine = IntentQueryEngine()
