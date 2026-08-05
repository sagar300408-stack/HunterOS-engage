"""
HunterOS Engage — Memory Context Gateway (Phase 2.1.5)

The single public read-only entry point and Anti-Corruption Layer (ACL) into the Memory domain
for all future intelligence modules (Conversation Intelligence, Intent Intelligence,
Customer Journey, Recommendations, Executive Dashboard).

Orchestrates read models, Knowledge Graph queries, ContextSchemaRegistry, and the
7-step ContextPipeline.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from app.domain.memory.graph.facade import KnowledgeGraphFacade
from app.domain.memory.intelligence.cache import (
    AbstractContextCache,
    NoOpContextCache,
)
from app.domain.memory.intelligence.export import (
    ContextExportEngine,
    default_context_export_engine,
)
from app.domain.memory.intelligence.models import (
    ComposedContext,
    ContextScope,
    ExportTargetFormat,
)
from app.domain.memory.intelligence.pipeline import ContextPipeline
from app.domain.memory.intelligence.registry import (
    ContextDescriptor,
    ContextSchemaRegistry,
    default_context_schema_registry,
)
from app.domain.memory.intelligence.schemas import ContextRequestOptions
from app.domain.memory.intelligence.strategies import (
    CompositionStrategyRegistry,
    default_strategy_registry,
)
from app.domain.memory.intelligence.validation import (
    ContextValidator,
    default_context_validator,
)
from app.domain.memory.interfaces.read_repository import AbstractMemoryReadRepository
from app.domain.memory.queries.facade import MemoryQueryFacade
from app.domain.memory.repositories.read_repository import (
    SqlAlchemyMemoryReadRepository,
)


class MemoryContextGateway:
    """
    Unified read-only Anti-Corruption Layer (ACL) for HunterOS Context & Intelligence.
    """

    def __init__(
        self,
        memory_read_repository: Optional[AbstractMemoryReadRepository] = None,
        memory_query_facade: Optional[MemoryQueryFacade] = None,
        knowledge_graph_facade: Optional[KnowledgeGraphFacade] = None,
        schema_registry: Optional[ContextSchemaRegistry] = None,
        strategy_registry: Optional[CompositionStrategyRegistry] = None,
        validator: Optional[ContextValidator] = None,
        export_engine: Optional[ContextExportEngine] = None,
        cache_provider: Optional[AbstractContextCache] = None,
    ) -> None:
        self._read_repo = memory_read_repository or SqlAlchemyMemoryReadRepository()
        self._query_facade = memory_query_facade or MemoryQueryFacade(self._read_repo)
        self._graph_facade = knowledge_graph_facade or KnowledgeGraphFacade()
        self._schema_registry = schema_registry or default_context_schema_registry
        self._strategy_registry = strategy_registry or default_strategy_registry
        self._validator = validator or default_context_validator
        self._export_engine = export_engine or default_context_export_engine
        self._cache = cache_provider or NoOpContextCache()

        self._pipeline = ContextPipeline(
            memory_read_repo=self._read_repo,
            memory_query_facade=self._query_facade,
            knowledge_graph_facade=self._graph_facade,
            schema_registry=self._schema_registry,
            strategy_registry=self._strategy_registry,
            validator=self._validator,
            export_engine=self._export_engine,
        )

    @property
    def schemas(self) -> ContextSchemaRegistry:
        """Access schema registry."""
        return self._schema_registry

    @property
    def strategies(self) -> CompositionStrategyRegistry:
        """Access strategy registry."""
        return self._strategy_registry

    @property
    def pipeline(self) -> ContextPipeline:
        """Access underlying deterministic 7-step pipeline."""
        return self._pipeline

    # ── High-Level Frozen Context APIs ────────────────────────────────────────

    async def get_customer_context(
        self,
        customer_id: str,
        workspace_id: Optional[uuid.UUID] = None,
        options: Optional[ContextRequestOptions] = None,
    ) -> Any:
        """Assembles Customer 360 Context."""
        return await self._pipeline.execute(
            scope=ContextScope.CUSTOMER,
            entity_id=customer_id,
            workspace_id=workspace_id,
            options=options,
        )

    async def get_organization_context(
        self,
        org_id: str,
        workspace_id: Optional[uuid.UUID] = None,
        options: Optional[ContextRequestOptions] = None,
    ) -> Any:
        """Assembles Organization & B2B Company Context."""
        return await self._pipeline.execute(
            scope=ContextScope.ORGANIZATION,
            entity_id=org_id,
            workspace_id=workspace_id,
            options=options,
            custom_entity_type="COMPANY",
        )

    async def get_opportunity_context(
        self,
        opportunity_id: str,
        workspace_id: Optional[uuid.UUID] = None,
        options: Optional[ContextRequestOptions] = None,
    ) -> Any:
        """Assembles Commercial Opportunity / Deal Context."""
        return await self._pipeline.execute(
            scope=ContextScope.OPPORTUNITY,
            entity_id=opportunity_id,
            workspace_id=workspace_id,
            options=options,
        )

    async def get_property_context(
        self,
        property_id: str,
        workspace_id: Optional[uuid.UUID] = None,
        options: Optional[ContextRequestOptions] = None,
    ) -> Any:
        """Assembles Real Estate Property Context."""
        return await self._pipeline.execute(
            scope=ContextScope.PROPERTY,
            entity_id=property_id,
            workspace_id=workspace_id,
            options=options,
        )

    async def get_executive_context(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        options: Optional[ContextRequestOptions] = None,
    ) -> Any:
        """Assembles Executive Workspace-Wide Intelligence Context."""
        return await self._pipeline.execute(
            scope=ContextScope.EXECUTIVE,
            entity_id=None,
            workspace_id=workspace_id,
            options=options,
        )

    async def get_custom_context(
        self,
        entity_type: str,
        entity_id: str,
        workspace_id: Optional[uuid.UUID] = None,
        options: Optional[ContextRequestOptions] = None,
    ) -> Any:
        """Assembles flexible custom entity context."""
        return await self._pipeline.execute(
            scope=ContextScope.CUSTOM,
            entity_id=entity_id,
            workspace_id=workspace_id,
            options=options,
            custom_entity_type=entity_type,
        )

    async def export_context(
        self,
        scope: ContextScope,
        entity_id: Optional[str] = None,
        workspace_id: Optional[uuid.UUID] = None,
        target_format: ExportTargetFormat = ExportTargetFormat.STRUCTURED_CONTEXT,
        options: Optional[ContextRequestOptions] = None,
    ) -> Any:
        """Export context in specialized target format."""
        opts = options or ContextRequestOptions(format=target_format)
        opts.format = target_format
        return await self._pipeline.execute(
            scope=scope,
            entity_id=entity_id,
            workspace_id=workspace_id,
            options=opts,
        )


# Global singleton instance
_gateway_instance: Optional[MemoryContextGateway] = None


def get_memory_context_gateway() -> MemoryContextGateway:
    """Retrieve global MemoryContextGateway singleton."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = MemoryContextGateway()
    return _gateway_instance


def set_memory_context_gateway(gateway: MemoryContextGateway) -> None:
    """Override gateway instance (for dependency injection & testing)."""
    global _gateway_instance
    _gateway_instance = gateway
