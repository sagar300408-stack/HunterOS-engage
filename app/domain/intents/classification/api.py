"""
HunterOS Engage V1 - Canonical Intent API v1
Single frozen contract for downstream Journey Intelligence, Recommendations, and Dashboard modules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from app.domain.conversations.analysis.models import ConversationAnalysisResult
from app.domain.conversations.insight.models import ConversationInsightResult
from app.domain.conversations.timeline.models import ConversationTimeline
from app.domain.intents.classification.engine import (
    IntentClassificationEngine,
    default_classification_engine,
)
from app.domain.intents.classification.models import (
    ClassifiedIntent,
    IntentClassificationResult,
    IntentGroup,
    IntentRelationship,
)
from app.domain.intents.classification.plugins.registry import (
    IndustryPluginRegistry,
    default_industry_plugin_registry,
)
from app.domain.intents.classification.process.registry import (
    BusinessProcessRegistry,
    default_business_process_registry,
)
from app.domain.intents.classification.query import (
    IntentClassificationQueryEngine,
    default_classification_query_engine,
)
from app.domain.intents.classification.repository import (
    InMemoryIntentClassificationRepository,
    default_classification_repository,
)
from app.domain.intents.classification.schemas import IntentAnalyticsQueryDTO
from app.domain.intents.classification.taxonomy.graph import (
    BusinessIntentTaxonomyGraph,
    default_taxonomy_graph,
)
from app.domain.intents.classification.views.audit import AuditClassificationView
from app.domain.intents.classification.views.executive import (
    ExecutiveClassificationView,
)
from app.domain.intents.classification.views.operations import (
    OperationsClassificationView,
)
from app.domain.intents.classification.views.sales import SalesClassificationView
from app.domain.intents.models import DetectedIntent, IntentDetectionResult


class CanonicalIntentAPIv1:
    """
    Unified, frozen public API interface for Intent Intelligence Classification.
    """

    def __init__(
        self,
        engine: Optional[IntentClassificationEngine] = None,
        repository: Optional[InMemoryIntentClassificationRepository] = None,
        query_engine: Optional[IntentClassificationQueryEngine] = None,
        taxonomy_graph: Optional[BusinessIntentTaxonomyGraph] = None,
        process_registry: Optional[BusinessProcessRegistry] = None,
        plugin_registry: Optional[IndustryPluginRegistry] = None,
    ):
        self._engine = engine or default_classification_engine
        self._repository = repository or default_classification_repository
        self._query_engine = query_engine or default_classification_query_engine
        self._taxonomy_graph = taxonomy_graph or default_taxonomy_graph
        self._process_registry = process_registry or default_business_process_registry
        self._plugin_registry = plugin_registry or default_industry_plugin_registry

        # Built-in Views
        self._views = {
            "executive": ExecutiveClassificationView(),
            "sales": SalesClassificationView(),
            "operations": OperationsClassificationView(),
            "audit": AuditClassificationView(),
        }

    def classify_conversation(
        self,
        conversation_id: str,
        detection_result: Optional[IntentDetectionResult] = None,
        detected_intents: Optional[List[DetectedIntent]] = None,
        analysis_result: Optional[ConversationAnalysisResult] = None,
        timeline: Optional[ConversationTimeline] = None,
        insight_result: Optional[ConversationInsightResult] = None,
        workspace_id: Optional[uuid.UUID] = None,
        customer_id: Optional[str] = None,
        active_plugins: Optional[List[str]] = None,
    ) -> IntentClassificationResult:
        """
        Classifies conversation intents and saves the result in the repository.
        """
        result = self._engine.classify(
            conversation_id=conversation_id,
            detection_result=detection_result,
            detected_intents=detected_intents,
            analysis_result=analysis_result,
            timeline=timeline,
            insight_result=insight_result,
            workspace_id=workspace_id,
            customer_id=customer_id,
            active_plugins=active_plugins,
        )
        self._repository.save(result)
        return result

    def get_classification(self, classification_id: uuid.UUID) -> Optional[IntentClassificationResult]:
        """Retrieve classification result by its unique UUID."""
        return self._repository.get_by_id(classification_id)

    def get_latest_classification_for_conversation(self, conversation_id: str) -> Optional[IntentClassificationResult]:
        """Retrieve the latest classification result for a conversation."""
        return self._repository.get_latest_by_conversation_id(conversation_id)

    def get_classified_intents_for_conversation(self, conversation_id: str) -> List[ClassifiedIntent]:
        """Retrieve all classified intents for a conversation."""
        res = self.get_latest_classification_for_conversation(conversation_id)
        return res.classified_intents if res else []

    def get_intent_relationships_for_conversation(self, conversation_id: str) -> List[IntentRelationship]:
        """Retrieve all inferred intent relationships for a conversation."""
        res = self.get_latest_classification_for_conversation(conversation_id)
        return res.relationships if res else []

    def get_intent_groups_for_conversation(self, conversation_id: str) -> List[IntentGroup]:
        """Retrieve all intent clusters for a conversation."""
        res = self.get_latest_classification_for_conversation(conversation_id)
        return res.groups if res else []

    def get_view(self, conversation_id: str, view_type: str) -> Optional[Dict[str, Any]]:
        """Generate a perspective projection view for a conversation."""
        res = self.get_latest_classification_for_conversation(conversation_id)
        if not res:
            return None
        view_handler = self._views.get(view_type.lower())
        if not view_handler:
            raise KeyError(f"Unsupported view type '{view_type}'. Valid views: {list(self._views.keys())}")
        return view_handler.generate(res)

    def run_analytics(self, workspace_id: Optional[uuid.UUID] = None) -> IntentAnalyticsQueryDTO:
        """Run descriptive analytics query across stored classifications."""
        return self._query_engine.run_analytics_query(workspace_id=workspace_id)

    def get_taxonomy_graph(self) -> BusinessIntentTaxonomyGraph:
        """Returns the active BusinessIntentTaxonomyGraph."""
        return self._taxonomy_graph

    def get_process_registry(self) -> BusinessProcessRegistry:
        """Returns the active BusinessProcessRegistry."""
        return self._process_registry

    def get_plugin_registry(self) -> IndustryPluginRegistry:
        """Returns the active IndustryPluginRegistry."""
        return self._plugin_registry


# Singleton default API instance
canonical_intent_api_v1 = CanonicalIntentAPIv1()
# Alias for backward compatibility
IntentClassificationAPIv1 = CanonicalIntentAPIv1
