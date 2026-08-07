"""
HunterOS Engage V1 - Intent Query Engine
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

High-performance deterministic query service for Intent Intelligence Contexts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.intents.integration.cache import IIntentContextCache, NullIntentContextCache
from app.domain.intents.integration.models import (
    CompositionProfileType,
    ContextGraphNode,
    IntentIntelligenceContext,
)
from app.domain.intents.integration.repository import IntentContextRepository, default_context_repository

logger = logging.getLogger(__name__)


class IntentQueryEngine:
    """
    Query Engine providing deterministic querying, caching, and graph navigation.
    """

    def __init__(
        self,
        repository: Optional[IntentContextRepository] = None,
        cache: Optional[IIntentContextCache] = None,
    ) -> None:
        self.repository = repository or default_context_repository
        self.cache = cache or NullIntentContextCache()

    def get_by_id(self, context_id: uuid.UUID) -> Optional[IntentIntelligenceContext]:
        cache_key = f"ctx_id:{context_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        ctx = self.repository.get_by_id(context_id)
        if ctx:
            self.cache.set(cache_key, ctx)
        return ctx

    def get_by_conversation(
        self,
        conversation_id: str,
        profile: Optional[Union[str, CompositionProfileType]] = None,
    ) -> Optional[IntentIntelligenceContext]:
        prof_enum = CompositionProfileType(profile) if isinstance(profile, str) and profile in CompositionProfileType.__members__ else (profile if isinstance(profile, CompositionProfileType) else None)
        cache_key = f"ctx_conv:{conversation_id}:{prof_enum.value if prof_enum else 'latest'}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        ctx = self.repository.get_by_conversation(conversation_id, profile=prof_enum)
        if ctx:
            self.cache.set(cache_key, ctx)
        return ctx

    def query(
        self,
        workspace_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        profile: Optional[Union[str, CompositionProfileType]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IntentIntelligenceContext]:
        prof_enum = CompositionProfileType(profile) if isinstance(profile, str) and profile in CompositionProfileType.__members__ else (profile if isinstance(profile, CompositionProfileType) else None)
        return self.repository.query(
            workspace_id=workspace_id,
            entity_id=entity_id,
            conversation_id=conversation_id,
            profile=prof_enum,
            limit=limit,
            offset=offset,
        )

    def get_intent_lineage(self, conversation_id: str, intent_id: str) -> List[ContextGraphNode]:
        ctx = self.get_by_conversation(conversation_id)
        if not ctx or not ctx.context_graph:
            return []
        return ctx.context_graph.get_lineage(intent_id)

    def get_intent_conflicts(self, conversation_id: str, intent_id: str) -> List[ContextGraphNode]:
        ctx = self.get_by_conversation(conversation_id)
        if not ctx or not ctx.context_graph:
            return []
        return ctx.context_graph.get_conflicts(intent_id)

    def get_intent_dependencies(self, conversation_id: str, intent_id: str) -> List[ContextGraphNode]:
        ctx = self.get_by_conversation(conversation_id)
        if not ctx or not ctx.context_graph:
            return []
        return ctx.context_graph.get_dependencies(intent_id)
