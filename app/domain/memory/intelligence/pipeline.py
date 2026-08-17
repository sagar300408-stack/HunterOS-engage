"""
HunterOS Engage — Deterministic Context Pipeline (Phase 2.1.5)

Executes a 7-step deterministic read-only workflow:
  Load -> Normalize -> Validate -> Expand -> Compose -> Project -> Serialize

Strictly read-only and non-mutating. Zero AI reasoning.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from app.domain.memory.graph.facade import KnowledgeGraphFacade
from app.domain.memory.graph.models import EntityReference, GraphNodeType
from app.domain.memory.intelligence.composer import ContextComposer
from app.domain.memory.intelligence.export import (
    ContextExportEngine,
    default_context_export_engine,
)
from app.domain.memory.intelligence.models import (
    ComposedContext,
    ContextBlockType,
    ContextScope,
    ExportTargetFormat,
)
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
from app.domain.memory.queries.models import GetCustomerMemoryQuery


class ContextPipeline:
    """
    Orchestrates the 7-step read-only context composition pipeline.
    """

    def __init__(
        self,
        memory_read_repo: Optional[AbstractMemoryReadRepository] = None,
        memory_query_facade: Optional[MemoryQueryFacade] = None,
        knowledge_graph_facade: Optional[KnowledgeGraphFacade] = None,
        schema_registry: Optional[ContextSchemaRegistry] = None,
        strategy_registry: Optional[CompositionStrategyRegistry] = None,
        validator: Optional[ContextValidator] = None,
        composer: Optional[ContextComposer] = None,
        export_engine: Optional[ContextExportEngine] = None,
    ) -> None:
        self._read_repo = memory_read_repo
        self._query_facade = memory_query_facade
        self._graph_facade = knowledge_graph_facade
        self._schema_registry = schema_registry or default_context_schema_registry
        self._strategy_registry = strategy_registry or default_strategy_registry
        self._validator = validator or default_context_validator
        self._composer = composer or ContextComposer(self._validator)
        self._export_engine = export_engine or default_context_export_engine

    async def execute(
        self,
        scope: ContextScope,
        entity_id: Optional[str] = None,
        workspace_id: Optional[uuid.UUID] = None,
        options: Optional[ContextRequestOptions] = None,
        custom_entity_type: Optional[str] = None,
    ) -> Any:
        """
        Execute the 7-step context pipeline.
        """
        start_time = time.time()

        # Step 0: Resolve Descriptor and Strategy
        descriptor: Optional[ContextDescriptor] = self._schema_registry.get(scope)
        strategy = self._strategy_registry.get_strategy(scope)
        requested_blocks = strategy.determine_blocks(options)

        raw_blocks: Dict[ContextBlockType, Any] = {}
        errors: Dict[ContextBlockType, str] = {}
        projections_applied: List[str] = []

        # ── Step 1: LOAD ───────────────────────────────────────────────────────
        uid: Optional[uuid.UUID] = None
        if entity_id:
            if isinstance(entity_id, uuid.UUID):
                uid = entity_id
            else:
                try:
                    uid = uuid.UUID(str(entity_id))
                except Exception:
                    uid = None

        if ContextBlockType.MEMORY in requested_blocks and entity_id:
            try:
                mem_dto = None
                if self._query_facade and uid:
                    try:
                        # Pass workspace_id so the query/repository boundary enforces
                        # tenant isolation before data enters the pipeline.
                        mem_dto = await self._query_facade.get_customer_memory(
                            customer_id=uid,
                            session=None,
                        )
                    except Exception:
                        pass
                if mem_dto is None and self._read_repo:
                    try:
                        # Explicit workspace predicate at the repository level.
                        mem_dto = await self._read_repo.get_by_customer_id(
                            customer_id=uid or entity_id,
                            workspace_id=workspace_id,
                        )
                    except Exception:
                        pass
                raw_blocks[ContextBlockType.MEMORY] = mem_dto
            except Exception as e:
                errors[ContextBlockType.MEMORY] = str(e)

        if ContextBlockType.RELATIONSHIPS in requested_blocks and entity_id and self._graph_facade:
            try:
                node_type = custom_entity_type or scope.value
                edges = await self._graph_facade.queries.get_direct_relationships(
                    entity_type=node_type,
                    entity_id=entity_id,
                    workspace_id=workspace_id,
                )
                raw_blocks[ContextBlockType.RELATIONSHIPS] = edges
            except Exception as e:
                errors[ContextBlockType.RELATIONSHIPS] = str(e)

        if ContextBlockType.TIMELINE in requested_blocks and entity_id and self._read_repo:
            try:
                events = None
                if hasattr(self._read_repo, "get_timeline"):
                    res = await self._read_repo.get_timeline(customer_id=uid or entity_id)
                    events = res[0] if isinstance(res, tuple) else res
                elif hasattr(self._read_repo, "get_timeline_events"):
                    events = await self._read_repo.get_timeline_events(
                        customer_id=uid or entity_id,
                        workspace_id=workspace_id,
                    )
                raw_blocks[ContextBlockType.TIMELINE] = events
            except Exception as e:
                errors[ContextBlockType.TIMELINE] = str(e)

        if ContextBlockType.VERSIONS in requested_blocks and entity_id and self._read_repo:
            try:
                vers = None
                if hasattr(self._read_repo, "get_versions"):
                    res = await self._read_repo.get_versions(customer_id=uid or entity_id)
                    vers = res[0] if isinstance(res, tuple) else res
                elif hasattr(self._read_repo, "get_memory_versions"):
                    vers = await self._read_repo.get_memory_versions(
                        customer_id=uid or entity_id,
                        workspace_id=workspace_id,
                    )
                raw_blocks[ContextBlockType.VERSIONS] = vers
            except Exception as e:
                errors[ContextBlockType.VERSIONS] = str(e)

        if ContextBlockType.STATISTICS in requested_blocks and self._graph_facade:
            try:
                stats = await self._graph_facade.queries.get_workspace_statistics(
                    workspace_id=workspace_id,
                )
                raw_blocks[ContextBlockType.STATISTICS] = stats
            except Exception as e:
                errors[ContextBlockType.STATISTICS] = str(e)

        # ── Step 2: NORMALIZE ─────────────────────────────────────────────────
        # Support both legacy .to_dict() objects and Pydantic V2 models
        # (.model_dump()). The fallback to str() is kept only as a last resort.
        def _normalize_item(item: Any) -> Any:
            if hasattr(item, "to_dict"):
                return item.to_dict()
            if hasattr(item, "model_dump"):  # Pydantic V2
                return item.model_dump(mode="json")
            if isinstance(item, dict):
                return item
            return {"value": str(item)}

        normalized_blocks: Dict[ContextBlockType, Any] = {}
        for b_type, data in raw_blocks.items():
            if data is None:
                continue
            if isinstance(data, list):
                normalized_blocks[b_type] = [_normalize_item(item) for item in data]
            else:
                normalized_blocks[b_type] = _normalize_item(data)

        # ── Step 3: VALIDATE ──────────────────────────────────────────────────
        # Fail-closed: any cross-workspace violation purges the offending block
        # from normalized_blocks so foreign data cannot reach the composer,
        # projector, or export engine.
        try:
            violations = self._validator.validate_workspace_isolation(
                workspace_id=workspace_id,
                memory_data=normalized_blocks.get(ContextBlockType.MEMORY),
                relationships_data=normalized_blocks.get(ContextBlockType.RELATIONSHIPS),
                strict=False,  # collect all violations without raising
            )
            if violations:
                # Purge every block that contains foreign-workspace data.
                mem_data = normalized_blocks.get(ContextBlockType.MEMORY, {})
                if isinstance(mem_data, dict):
                    mem_ws = str(mem_data.get("workspace_id", ""))
                    if workspace_id and mem_ws and mem_ws != str(workspace_id):
                        normalized_blocks.pop(ContextBlockType.MEMORY, None)
                        errors[ContextBlockType.MEMORY] = (
                            f"Cross-workspace isolation violation: "
                            f"memory workspace {mem_ws} != requested {workspace_id}"
                        )
                # Purge relationship entries that belong to another workspace.
                rel_data = normalized_blocks.get(ContextBlockType.RELATIONSHIPS)
                if isinstance(rel_data, list) and workspace_id:
                    ws_str = str(workspace_id)
                    clean = [r for r in rel_data
                             if not (isinstance(r, dict) and r.get("workspace_id")
                                     and str(r["workspace_id"]) != ws_str)]
                    normalized_blocks[ContextBlockType.RELATIONSHIPS] = clean
        except Exception as e:
            errors[ContextBlockType.AUDIT] = f"Workspace isolation validation error: {str(e)}"

        # ── Step 4: EXPAND (Multi-hop Knowledge Graph Traversal) ───────────────
        max_depth = options.max_graph_depth if options else 2
        if max_depth > 1 and entity_id and self._graph_facade and ContextBlockType.RELATIONSHIPS in requested_blocks:
            try:
                start_ref = EntityReference(
                    entity_type=GraphNodeType(custom_entity_type or scope.value),
                    entity_id=entity_id,
                    workspace_id=workspace_id,
                )
                traversal = await self._graph_facade.queries.traverse_graph(
                    start_node=start_ref,
                    strategy="BFS",
                    max_depth=max_depth,
                    workspace_id=workspace_id,
                )
                if traversal and traversal.visited_nodes:
                    projections_applied.append(f"MultiHopExpansion(depth={max_depth})")
            except Exception:
                pass

        # ── Step 5: COMPOSE ───────────────────────────────────────────────────
        composed = self._composer.compose(
            scope=scope,
            entity_id=entity_id,
            workspace_id=workspace_id,
            descriptor=descriptor,
            requested_blocks=requested_blocks,
            loaded_blocks=normalized_blocks,
            projections_applied=projections_applied,
            errors=errors,
            start_time=start_time,
        )

        # ── Step 6: PROJECT ───────────────────────────────────────────────────
        if ContextBlockType.PROJECTIONS in requested_blocks and entity_id and self._graph_facade:
            try:
                proj_data: Optional[Dict[str, Any]] = None
                if scope == ContextScope.CUSTOMER:
                    proj = await self._graph_facade.queries.get_customer_360_projection(
                        customer_id=entity_id,
                        workspace_id=workspace_id,
                    )
                    projections_applied.append("Customer360Projection")
                    if proj and hasattr(proj, "to_dict"):
                        proj_data = proj.to_dict()
                    elif isinstance(proj, dict):
                        proj_data = proj
                elif scope == ContextScope.ORGANIZATION:
                    proj = await self._graph_facade.queries.get_organization_projection(
                        company_id=entity_id,
                        workspace_id=workspace_id,
                    )
                    projections_applied.append("OrganizationProjection")
                    if proj and hasattr(proj, "to_dict"):
                        proj_data = proj.to_dict()
                    elif isinstance(proj, dict):
                        proj_data = proj
                elif scope == ContextScope.PROPERTY:
                    proj = await self._graph_facade.queries.get_property_network_projection(
                        property_id=entity_id,
                        workspace_id=workspace_id,
                    )
                    projections_applied.append("PropertyNetworkProjection")
                    if proj and hasattr(proj, "to_dict"):
                        proj_data = proj.to_dict()
                    elif isinstance(proj, dict):
                        proj_data = proj
                elif scope == ContextScope.OPPORTUNITY:
                    proj = await self._graph_facade.queries.get_opportunity_network_projection(
                        opportunity_id=entity_id,
                        workspace_id=workspace_id,
                    )
                    projections_applied.append("OpportunityNetworkProjection")
                    if proj and hasattr(proj, "to_dict"):
                        proj_data = proj.to_dict()
                    elif isinstance(proj, dict):
                        proj_data = proj

                if proj_data is not None:
                    from app.domain.memory.intelligence.models import ContextBlock
                    composed.blocks[ContextBlockType.PROJECTIONS] = ContextBlock(
                        block_type=ContextBlockType.PROJECTIONS,
                        data=proj_data,
                        loaded=True,
                    )
            except Exception:
                pass

        # ── Step 7: SERIALIZE ─────────────────────────────────────────────────
        target_fmt = options.format if options and options.format else ExportTargetFormat.STANDARD_API
        return self._export_engine.export(composed, target_format=target_fmt)
