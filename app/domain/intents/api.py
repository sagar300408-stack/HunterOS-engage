"""
HunterOS Engage V1 - Frozen Intent Detection Public API v1
Official programmatic interface for downstream modules consuming Intent Intelligence.
Downstream bounded contexts must only consume this frozen public API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.models import ConversationAnalysisResult
from app.domain.conversations.insight.models import ConversationInsightResult
from app.domain.conversations.timeline.models import ConversationTimeline
from app.domain.intents.engine import (
    IntentDetectionEngine,
    default_intent_detection_engine,
)
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    IntentDetectionResult,
    IntentTaxonomyCategory,
    IntentType,
)
from app.domain.intents.taxonomy import IntentTaxonomy


class IntentDetectionAPIv1:
    """
    Frozen Public API v1 for Intent Intelligence.
    Ensures strict boundary decoupling and deterministic contract stability.
    """

    def __init__(self, engine: Optional[IntentDetectionEngine] = None):
        self._engine = engine or default_intent_detection_engine

    def detect_intents(
        self,
        analysis_result: Optional[ConversationAnalysisResult] = None,
        timeline: Optional[ConversationTimeline] = None,
        insight_result: Optional[ConversationInsightResult] = None,
        conversation_id: Optional[str] = None,
        workspace_id: Optional[uuid.UUID] = None,
        customer_id: Optional[str] = None,
    ) -> IntentDetectionResult:
        """Execute intent detection over provided conversation artifacts."""
        return self._engine.detect_intents(
            analysis_result=analysis_result,
            timeline=timeline,
            insight_result=insight_result,
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            customer_id=customer_id,
        )

    def get_conversation_intents(
        self, conversation_id: str
    ) -> Optional[IntentDetectionResult]:
        """Fetch cached intent detection results for a conversation."""
        return self._engine.query_engine.get_conversation_intents(conversation_id)

    def get_intent_by_id(
        self, conversation_id: str, intent_id: uuid.UUID
    ) -> Optional[DetectedIntent]:
        """Fetch a single intent by ID."""
        return self._engine.query_engine.get_intent_by_id(conversation_id, intent_id)

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
        """Query across all detected intents matching criteria."""
        return self._engine.query_engine.query(
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
        """Project intent detection results into a specific perspective (executive, sales, operations, audit)."""
        return self._engine.query_engine.render_view(conversation_id, view_name)

    def get_taxonomy_tree(self) -> Dict[str, Any]:
        """Return the complete hierarchical taxonomy structure."""
        return IntentTaxonomy.get_taxonomy_tree()


# Frozen public API v1 instance
intent_api_v1 = IntentDetectionAPIv1()
