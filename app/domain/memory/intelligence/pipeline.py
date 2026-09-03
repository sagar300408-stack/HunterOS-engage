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
                except ValueError:
                    pass

        if ContextBlockType.MEMORY in requested_blocks and entity_id:
            try:
                mem_dto = None
                if self._query_facade and uid:
                    mem_dto = await self._query_facade.get_customer_memory(
                        customer_id=uid,
                        session=None,
                    )
                if mem_dto is None and self._read_repo:
                    # Explicit workspace predicate at the repository level.
                    mem_dto = await self._read_repo.get_by_customer_id(
                        customer_id=uid or entity_id,
                        workspace_id=workspace_id,
                    )
                if mem_dto is not None:
                    raw_blocks[ContextBlockType.MEMORY] = mem_dto
            except Exception as e:
                errors[ContextBlockType.MEMORY] = f"Retrieval failure: {str(e)}"

        if ContextBlockType.RELATIONSHIPS in requested_blocks and entity_id and self._graph_facade:
            try:
                node_type = custom_entity_type or scope.value
                edges = await self._graph_facade.queries.get_direct_relationships(
                    entity_type=node_type,
                    entity_id=str(entity_id),
                    workspace_id=workspace_id,
                )
                raw_blocks[ContextBlockType.RELATIONSHIPS] = edges
            except Exception as e:
                errors[ContextBlockType.RELATIONSHIPS] = f"Graph retrieval failure: {str(e)}"

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
                if events is not None:
                    raw_blocks[ContextBlockType.TIMELINE] = events
            except Exception as e:
                errors[ContextBlockType.TIMELINE] = f"Retrieval failure: {str(e)}"

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
                if vers is not None:
                    raw_blocks[ContextBlockType.VERSIONS] = vers
            except Exception as e:
                errors[ContextBlockType.VERSIONS] = f"Retrieval failure: {str(e)}"

        if ContextBlockType.STATISTICS in requested_blocks and self._graph_facade:
            try:
                stats = await self._graph_facade.queries.get_statistics(
                    workspace_id=workspace_id,
                    session=None,
                )
                raw_blocks[ContextBlockType.STATISTICS] = stats
            except Exception as e:
                errors[ContextBlockType.STATISTICS] = f"Graph retrieval failure: {str(e)}"

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
        # Fail-closed: any cross-workspace violation MUST raise CrossWorkspaceContextError.
        # This prevents the context from proceeding to composer, projector, or export engine.
        from app.domain.memory.intelligence.validation import CrossWorkspaceContextError
        
        try:
            violations = self._validator.validate_workspace_isolation(
                workspace_id=workspace_id,
                memory_data=normalized_blocks.get(ContextBlockType.MEMORY),
                relationships_data=normalized_blocks.get(ContextBlockType.RELATIONSHIPS),
                strict=True,  # STRICT MODE: raises CrossWorkspaceContextError on violation
            )
        except CrossWorkspaceContextError as e:
            # We explicitly catch and re-raise to guarantee fail-closed security boundary.
            raise e
        except Exception as e:
            errors[ContextBlockType.AUDIT] = f"Workspace isolation validation error: {str(e)}"

        # ── Step 4: EXPAND (Multi-hop Knowledge Graph Traversal) ───────────────
        max_depth = options.max_graph_depth if options else 2
        if max_depth > 1 and entity_id and self._graph_facade and ContextBlockType.RELATIONSHIPS in requested_blocks:
            try:
                start_ref = EntityReference(
                    entity_type=GraphNodeType(custom_entity_type or scope.value),
                    entity_id=str(entity_id),
                    workspace_id=workspace_id,
                )
                traversal = await self._graph_facade.queries.traverse_neighbors(
                    workspace_id=workspace_id,
                    start_entity_type=start_ref.entity_type,
                    start_entity_id=start_ref.entity_id,
                    max_depth=max_depth,
                    strategy_name="bfs",
                )
                if traversal and traversal.nodes:
                    projections_applied.append(f"MultiHopExpansion(depth={max_depth})")
                    
                    # Merge multi-hop expanded edges into RELATIONSHIPS block
                    if traversal.edges:
                        expanded_edges = [_normalize_item(e) for e in traversal.edges]
                        existing_edges = normalized_blocks.get(ContextBlockType.RELATIONSHIPS) or []
                        seen_ids = {str(e.get("id")) for e in existing_edges if isinstance(e, dict) and "id" in e}
                        for edge_dict in expanded_edges:
                            eid = str(edge_dict.get("id")) if isinstance(edge_dict, dict) else None
                            if not eid or eid not in seen_ids:
                                existing_edges.append(edge_dict)
                                if eid:
                                    seen_ids.add(eid)
                        normalized_blocks[ContextBlockType.RELATIONSHIPS] = existing_edges

                    # Expose multi-hop traversed nodes
                    traversed_nodes = [_normalize_item(n) for n in traversal.nodes]
                    if ContextBlockType.PROJECTIONS in requested_blocks:
                        proj_dict = normalized_blocks.get(ContextBlockType.PROJECTIONS) or {}
                        if isinstance(proj_dict, dict):
                            proj_dict["graph_traversal"] = {
                                "depth": max_depth,
                                "nodes": traversed_nodes,
                                "total_nodes": len(traversed_nodes),
                                "paths": traversal.paths,
                            }
                            normalized_blocks[ContextBlockType.PROJECTIONS] = proj_dict
            except Exception as e:
                errors[ContextBlockType.RELATIONSHIPS] = f"Graph traversal failure: {str(e)}"

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
                    proj = await self._graph_facade.queries.project_customer_360(
                        workspace_id=workspace_id,
                        customer_id=str(entity_id),
                    )
                    projections_applied.append("Customer360Projection")
                    if proj and hasattr(proj, "to_dict"):
                        proj_data = proj.to_dict()
                    elif isinstance(proj, dict):
                        proj_data = proj
                elif scope == ContextScope.ORGANIZATION:
                    proj = await self._graph_facade.queries.project_organization(
                        workspace_id=workspace_id,
                        company_id=str(entity_id),
                    )
                    projections_applied.append("OrganizationProjection")
                    if proj and hasattr(proj, "to_dict"):
                        proj_data = proj.to_dict()
                    elif isinstance(proj, dict):
                        proj_data = proj
                elif scope == ContextScope.PROPERTY:
                    proj = await self._graph_facade.queries.project_property_network(
                        workspace_id=workspace_id,
                        property_id=str(entity_id),
                    )
                    projections_applied.append("PropertyNetworkProjection")
                    if proj and hasattr(proj, "to_dict"):
                        proj_data = proj.to_dict()
                    elif isinstance(proj, dict):
                        proj_data = proj
                elif scope == ContextScope.OPPORTUNITY:
                    proj = await self._graph_facade.queries.project_opportunity_network(
                        workspace_id=workspace_id,
                        opportunity_id=str(entity_id),
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
            except Exception as e:
                errors[ContextBlockType.PROJECTIONS] = f"Projection failure: {str(e)}"

        # ── Step 7: SERIALIZE ─────────────────────────────────────────────────
        target_fmt = options.format if options and options.format else ExportTargetFormat.STANDARD_API
        return self._export_engine.export(composed, target_format=target_fmt)
