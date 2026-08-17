"""
HunterOS Engage — Refinement Phase 2.1.5 Memory Context Integration Layer Test Suite

Certifies:
- MemoryContextGateway read-only semantics & orchestration
- ContextSchemaRegistry & extensible descriptor lookup
- ContextLineage provenance & ContextMetadata tracking
- ContextValidator & deterministic ContextCompletenessReport
- Composition strategies (Customer360, Organization, Property, Executive, Selective)
- 7-step deterministic ContextPipeline (Load -> Normalize -> Validate -> Expand -> Compose -> Project -> Serialize)
- ContextExportEngine (Standard API, Executive DTO, Dashboard DTO, StructuredContextDTO)
- AbstractContextCache contract & InMemoryContextCache provider
- Frozen REST API endpoints under /api/v1/memory/context
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.domain.conversations.models
from app.domain.memory.graph.export import GraphExportEngine
from app.domain.memory.graph.facade import KnowledgeGraphFacade
from app.domain.memory.graph.models import (
    EntityReference,
    GraphNodeType,
    RelationshipAggregate,
    RelationshipDirection,
    RelationshipMetadata,
    RelationshipStatus,
    RelationshipType,
)
from app.domain.memory.graph.storage import AbstractGraphStorageProvider
from app.domain.memory.intelligence.cache import (
    AbstractContextCache,
    InMemoryContextCache,
    NoOpContextCache,
)
from app.domain.memory.intelligence.composer import ContextComposer
from app.domain.memory.intelligence.export import (
    ContextExportEngine,
    default_context_export_engine,
)
from app.domain.memory.intelligence.gateway import (
    MemoryContextGateway,
    get_memory_context_gateway,
    set_memory_context_gateway,
)
from app.domain.memory.intelligence.models import (
    ComposedContext,
    ContextBlockType,
    ContextCompletenessReport,
    ContextCompletenessStatus,
    ContextLineage,
    ContextMetadata,
    ContextScope,
    ExportTargetFormat,
)
from app.domain.memory.intelligence.pipeline import ContextPipeline
from app.domain.memory.intelligence.registry import (
    ContextDescriptor,
    ContextSchemaRegistry,
    default_context_schema_registry,
)
from app.domain.memory.intelligence.schemas import (
    ContextRequestOptions,
    CustomContextRequest,
    DashboardContextExportDTO,
    ExecutiveContextExportDTO,
    StructuredContextDTO,
)
from app.domain.memory.intelligence.strategies import (
    CompositionStrategyRegistry,
    Customer360CompositionStrategy,
    ExecutiveCompositionStrategy,
    OpportunityCompositionStrategy,
    OrganizationCompositionStrategy,
    PropertyCompositionStrategy,
    SelectiveCompositionStrategy,
    default_strategy_registry,
)
from app.domain.memory.intelligence.validation import (
    ContextValidator,
    CrossWorkspaceContextError,
    default_context_validator,
)
from app.domain.memory.interfaces.read_repository import AbstractMemoryReadRepository
from app.domain.memory.models import (
    CustomerMemory,
    CustomerMemoryTimelineEvent,
    CustomerMemoryVersion,
    LifecycleStatus,
    MemoryChangeLog,
    MemoryImportance,
    MemoryTimelineCategory,
)
from app.domain.memory.queries.facade import MemoryQueryFacade
from app.main import create_app


# ── In-Memory Repositories for Isolated Integration Testing ──────────────────

class InMemoryMemoryReadRepository(AbstractMemoryReadRepository):
    """Deterministic in-memory CustomerMemory read repository."""

    def __init__(self) -> None:
        self.memories: Dict[str, CustomerMemory] = {}
        self.timeline_events: Dict[str, List[CustomerMemoryTimelineEvent]] = {}
        self.versions: Dict[str, List[CustomerMemoryVersion]] = {}
        self.change_logs: Dict[str, List[MemoryChangeLog]] = {}

    def get_model_class(self) -> Type[CustomerMemory]:
        return CustomerMemory

    def add_memory(self, memory: CustomerMemory) -> None:
        self.memories[str(memory.customer_id)] = memory
        self.memories[str(memory.id)] = memory

    async def get_by_customer_id(
        self,
        customer_id: Any,
        include_deleted: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> Optional[CustomerMemory]:
        mem = self.memories.get(str(customer_id))
        if mem and (include_deleted or not mem.is_deleted):
            return mem
        return None

    async def get_by_id(
        self,
        memory_id: Any,
        include_deleted: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> Optional[CustomerMemory]:
        mem = self.memories.get(str(memory_id))
        if mem and (include_deleted or not mem.is_deleted):
            return mem
        return None

    async def get_multiple(
        self,
        customer_ids: List[Any],
        include_deleted: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> List[CustomerMemory]:
        results = []
        for cid in customer_ids:
            mem = await self.get_by_customer_id(cid, include_deleted=include_deleted)
            if mem:
                results.append(mem)
        return results

    async def execute_query_plan_offset(
        self,
        plan: Any,
        session: Optional[AsyncSession] = None,
    ) -> Tuple[List[CustomerMemory], int]:
        items = list(self.memories.values())
        return items, len(items)

    async def execute_query_plan_cursor(
        self,
        plan: Any,
        expected_workspace_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None,
    ) -> Tuple[List[CustomerMemory], bool, Optional[str], Optional[str]]:
        items = list(self.memories.values())
        return items, False, None, None

    async def aggregate_memory_statistics(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        return {
            "total_memories": len(self.memories),
            "active_memories": len(self.memories),
            "archived_memories": 0,
            "locked_memories": 0,
            "storage_size_bytes": 1024,
            "avg_versions_per_customer": 1.0,
        }

    async def search(
        self,
        session: Optional[AsyncSession] = None,
        workspace_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> Tuple[List[CustomerMemory], int]:
        items = list(self.memories.values())
        return items, len(items)

    async def get_timeline(
        self,
        customer_id: Any,
        category: Optional[MemoryTimelineCategory] = None,
        event_type: Optional[str] = None,
        importance: Optional[MemoryImportance] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> Tuple[List[CustomerMemoryTimelineEvent], int]:
        events = self.timeline_events.get(str(customer_id), [])
        return events, len(events)

    async def get_versions(
        self,
        customer_id: Any,
        page: int = 1,
        page_size: int = 50,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> Tuple[List[CustomerMemoryVersion], int]:
        vers = self.versions.get(str(customer_id), [])
        return vers, len(vers)

    async def get_version_by_number(
        self,
        customer_id: Any,
        version_number: int,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> Optional[CustomerMemoryVersion]:
        for v in self.versions.get(str(customer_id), []):
            if v.version_number == version_number:
                return v
        return None

    async def get_change_logs(
        self,
        customer_id: Any,
        version_number: Optional[int] = None,
        field_path: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> Tuple[List[MemoryChangeLog], int]:
        logs = self.change_logs.get(str(customer_id), [])
        return logs, len(logs)

    async def bulk_get(
        self,
        customer_ids: List[Any],
        include_deleted: bool = False,
        session: Optional[AsyncSession] = None,
        **kwargs: Any,
    ) -> List[CustomerMemory]:
        return await self.get_multiple(customer_ids, include_deleted=include_deleted)


class InMemoryGraphStorageProvider(AbstractGraphStorageProvider):
    """In-memory Graph Storage Provider for fast deterministic testing."""

    def __init__(self) -> None:
        self.records: Dict[uuid.UUID, Dict[str, Any]] = {}

    async def save_relationship(self, aggregate: RelationshipAggregate, session: Any = None) -> RelationshipAggregate:
        self.records[aggregate.id] = aggregate.to_dict()
        return aggregate

    async def update_relationship(self, aggregate: RelationshipAggregate, session: Any = None) -> RelationshipAggregate:
        self.records[aggregate.id] = aggregate.to_dict()
        return aggregate

    async def get_relationship_by_id(self, relationship_id: uuid.UUID, session: Any = None) -> Optional[RelationshipAggregate]:
        data = self.records.get(relationship_id)
        if not data:
            return None
        return RelationshipAggregate.from_dict(data)

    async def query_relationships(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        relationship_types: Optional[List[str | RelationshipType]] = None,
        statuses: Optional[List[str | RelationshipStatus]] = None,
        min_strength: Optional[float] = None,
        min_confidence: Optional[float] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        results = []
        rel_type_strs = [rt.value if hasattr(rt, "value") else str(rt) for rt in relationship_types] if relationship_types else None
        status_strs = [st.value if hasattr(st, "value") else str(st) for st in statuses] if statuses else None

        for data in self.records.values():
            if workspace_id and str(data.get("workspace_id")) != str(workspace_id):
                continue
            if not include_deleted and data["is_deleted"]:
                continue
            if status_strs and data["status"] not in status_strs:
                continue
            if rel_type_strs and data["relationship_type"] not in rel_type_strs:
                continue
            if entity_type and entity_id:
                src_match = (data["source_node"]["entity_type"] == entity_type and str(data["source_node"]["entity_id"]) == str(entity_id))
                tgt_match = (data["target_node"]["entity_type"] == entity_type and str(data["target_node"]["entity_id"]) == str(entity_id))
                if not (src_match or tgt_match):
                    continue
            if min_strength is not None and data["strength"] < min_strength:
                continue
            if min_confidence is not None and data["metadata"]["confidence"] < min_confidence:
                continue
            results.append(RelationshipAggregate.from_dict(data))
        return results[offset:offset + limit]

    async def get_incident_edges(
        self,
        workspace_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: str,
        direction: str = "ALL",
        include_deleted: bool = False,
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        results = []
        for data in self.records.values():
            if workspace_id and str(data.get("workspace_id")) != str(workspace_id):
                continue
            if not include_deleted and data["is_deleted"]:
                continue
            if data["status"] != "ACTIVE":
                continue

            src_type = data["source_node"]["entity_type"]
            src_type_str = src_type.value if hasattr(src_type, "value") else str(src_type)
            tgt_type = data["target_node"]["entity_type"]
            tgt_type_str = tgt_type.value if hasattr(tgt_type, "value") else str(tgt_type)
            req_type_str = entity_type.value if hasattr(entity_type, "value") else str(entity_type)

            src_match = (src_type_str == req_type_str and str(data["source_node"]["entity_id"]) == str(entity_id))
            tgt_match = (tgt_type_str == req_type_str and str(data["target_node"]["entity_id"]) == str(entity_id))

            d = direction.upper()
            if d == "OUTGOING" and src_match:
                results.append(RelationshipAggregate.from_dict(data))
            elif d == "INCOMING" and tgt_match:
                results.append(RelationshipAggregate.from_dict(data))
            elif d == "ALL" and (src_match or tgt_match):
                results.append(RelationshipAggregate.from_dict(data))
        return results

    async def get_all_active_edges_for_workspace(
        self,
        workspace_id: Optional[uuid.UUID],
        session: Any = None,
    ) -> List[RelationshipAggregate]:
        results = []
        for data in self.records.values():
            if workspace_id and str(data.get("workspace_id")) != str(workspace_id):
                continue
            if data["is_deleted"] or data["status"] != "ACTIVE":
                continue
            results.append(RelationshipAggregate.from_dict(data))
        return results


# ── Test Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def test_workspace_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def in_memory_read_repo() -> InMemoryMemoryReadRepository:
    return InMemoryMemoryReadRepository()


@pytest.fixture
def in_memory_graph_storage() -> InMemoryGraphStorageProvider:
    return InMemoryGraphStorageProvider()


@pytest.fixture
def context_gateway(
    in_memory_read_repo: InMemoryMemoryReadRepository,
    in_memory_graph_storage: InMemoryGraphStorageProvider,
) -> MemoryContextGateway:
    query_facade = MemoryQueryFacade(in_memory_read_repo)
    graph_facade = KnowledgeGraphFacade(storage_provider=in_memory_graph_storage)
    gw = MemoryContextGateway(
        memory_read_repository=in_memory_read_repo,
        memory_query_facade=query_facade,
        knowledge_graph_facade=graph_facade,
    )
    set_memory_context_gateway(gw)
    return gw


# ── Test Cases ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gateway_initialization_and_read_only(context_gateway: MemoryContextGateway):
    """Verify gateway initializes as a read-only ACL."""
    assert context_gateway.schemas is not None
    assert context_gateway.strategies is not None
    assert context_gateway.pipeline is not None

    # Ensure no mutating command bus or write repo is directly exposed on gateway public API
    assert not hasattr(context_gateway, "commands")
    assert not hasattr(context_gateway, "mutate")
    assert not hasattr(context_gateway, "save_memory")


@pytest.mark.asyncio
async def test_context_schema_registry():
    """Verify dynamic registration and resolution of context schemas."""
    registry = ContextSchemaRegistry()

    # Verify built-ins
    cust_desc = registry.get("CUSTOMER")
    assert cust_desc is not None
    assert cust_desc.scope == ContextScope.CUSTOMER
    assert ContextBlockType.MEMORY in cust_desc.default_blocks
    assert ContextBlockType.MEMORY in cust_desc.required_blocks

    org_desc = registry.get(ContextScope.ORGANIZATION)
    assert org_desc is not None
    assert org_desc.name == "ORGANIZATION"

    # Register custom schema
    custom_desc = ContextDescriptor(
        name="CONVERSATION_INSIGHTS_V1",
        scope=ContextScope.CUSTOM,
        default_blocks=[ContextBlockType.MEMORY, ContextBlockType.TIMELINE],
        description="Future conversation intelligence schema descriptor.",
        schema_version="2.0.0",
        is_custom=True,
    )
    registry.register(custom_desc)

    resolved = registry.get("CONVERSATION_INSIGHTS_V1")
    assert resolved is not None
    assert resolved.schema_version == "2.0.0"
    assert resolved.is_custom is True


@pytest.mark.asyncio
async def test_context_lineage_and_metadata(test_workspace_id: uuid.UUID):
    """Verify ContextLineage captures exact provenance IDs deterministically."""
    mem_id = str(uuid.uuid4())
    rel_id = str(uuid.uuid4())
    tl_id = str(uuid.uuid4())

    composer = ContextComposer()
    composed = composer.compose(
        scope=ContextScope.CUSTOMER,
        entity_id="cust-123",
        workspace_id=test_workspace_id,
        descriptor=default_context_schema_registry.get("CUSTOMER"),
        requested_blocks=[ContextBlockType.MEMORY, ContextBlockType.RELATIONSHIPS, ContextBlockType.TIMELINE],
        loaded_blocks={
            ContextBlockType.MEMORY: {"id": mem_id, "customer_id": "cust-123"},
            ContextBlockType.RELATIONSHIPS: [{"id": rel_id, "source_id": "cust-123"}],
            ContextBlockType.TIMELINE: [{"id": tl_id, "category": "INTERACTION"}],
        },
        projections_applied=["Customer360Projection"],
    )

    assert composed.metadata.context_id is not None
    assert composed.metadata.context_version == 1
    assert composed.metadata.workspace_id == test_workspace_id

    assert mem_id in composed.lineage.source_memory_ids
    assert rel_id in composed.lineage.source_relationship_ids
    assert tl_id in composed.lineage.source_timeline_event_ids
    assert "Customer360Projection" in composed.lineage.projections_applied
    assert "memory_foundation" in composed.lineage.source_modules


@pytest.mark.asyncio
async def test_context_validation_and_completeness(test_workspace_id: uuid.UUID):
    """Verify ContextValidator calculates completeness score and isolates workspaces."""
    validator = ContextValidator()

    # 1. Completeness Evaluation
    descriptor = default_context_schema_registry.get("CUSTOMER")
    report = validator.evaluate_completeness(
        descriptor=descriptor,
        requested_blocks=[ContextBlockType.MEMORY, ContextBlockType.RELATIONSHIPS],
        loaded_blocks={
            ContextBlockType.MEMORY: {"id": "1", "name": "Test"},
            ContextBlockType.RELATIONSHIPS: [{"id": "r1"}],
        },
    )
    assert report.score == 1.0
    assert report.status == ContextCompletenessStatus.COMPLETE
    assert report.is_valid is True

    # 2. Degraded / Missing required block
    missing_report = validator.evaluate_completeness(
        descriptor=descriptor,
        requested_blocks=[ContextBlockType.MEMORY, ContextBlockType.RELATIONSHIPS],
        loaded_blocks={
            ContextBlockType.MEMORY: {},  # Empty required block
            ContextBlockType.RELATIONSHIPS: [{"id": "r1"}],
        },
    )
    assert missing_report.score < 1.0
    assert missing_report.is_valid is False

    # 3. Cross-Workspace Security Violation
    other_ws = uuid.uuid4()
    with pytest.raises(CrossWorkspaceContextError):
        validator.validate_workspace_isolation(
            workspace_id=test_workspace_id,
            memory_data={"workspace_id": str(other_ws)},
            relationships_data=None,
            strict=True,
        )


@pytest.mark.asyncio
async def test_composition_strategies():
    """Verify pluggable composition strategies select appropriate blocks."""
    registry = CompositionStrategyRegistry()

    cust_strat = registry.get_strategy(ContextScope.CUSTOMER)
    assert isinstance(cust_strat, Customer360CompositionStrategy)
    blocks = cust_strat.determine_blocks()
    assert ContextBlockType.MEMORY in blocks
    assert ContextBlockType.RELATIONSHIPS in blocks
    assert ContextBlockType.TIMELINE in blocks

    org_strat = registry.get_strategy("ORGANIZATION")
    assert isinstance(org_strat, OrganizationCompositionStrategy)
    org_blocks = org_strat.determine_blocks()
    assert ContextBlockType.RELATIONSHIPS in org_blocks
    assert ContextBlockType.MEMORY not in org_blocks

    exec_strat = registry.get_strategy("EXECUTIVE")
    assert isinstance(exec_strat, ExecutiveCompositionStrategy)
    assert ContextBlockType.STATISTICS in exec_strat.determine_blocks()

    selective_strat = registry.get_strategy("SELECTIVE")
    opts = ContextRequestOptions(blocks=["MEMORY", "STATISTICS"])
    sel_blocks = selective_strat.determine_blocks(opts)
    assert sel_blocks == [ContextBlockType.MEMORY, ContextBlockType.STATISTICS]


@pytest.mark.asyncio
async def test_7_step_pipeline_customer_context(
    test_workspace_id: uuid.UUID,
    in_memory_read_repo: InMemoryMemoryReadRepository,
    context_gateway: MemoryContextGateway,
):
    """Verify 7-step pipeline end-to-end execution for Customer scope."""
    customer_id = str(uuid.uuid4())
    mem = CustomerMemory(
        id=uuid.uuid4(),
        customer_id=uuid.UUID(customer_id),
        workspace_id=test_workspace_id,
        version_number=1,
        revision_id=1,
        lifecycle_status=LifecycleStatus.ACTIVE,
        is_deleted=False,
        memory_payload={
            "identity": {"full_name": "Sarah Connor", "primary_email": "sarah@skynet.com"},
            "personal_info": {"notes": "Key resistance contact"},
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    in_memory_read_repo.add_memory(mem)

    # Seed relationship in Knowledge Graph
    graph_facade = context_gateway._pipeline._graph_facade
    await graph_facade.commands.create_relationship(
        source=EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id=customer_id, workspace_id=test_workspace_id),
        target=EntityReference(entity_type=GraphNodeType.COMPANY, entity_id="cyberdyne-sys", workspace_id=test_workspace_id),
        relationship_type=RelationshipType.WORKS_FOR,
        workspace_id=test_workspace_id,
    )

    # Execute gateway context retrieval
    options = ContextRequestOptions(max_graph_depth=2, include_timeline=True)
    res = await context_gateway.get_customer_context(
        customer_id=customer_id,
        workspace_id=test_workspace_id,
        options=options,
    )

    assert res is not None
    assert res["scope"] == "CUSTOMER"
    assert res["entity_id"] == customer_id
    assert "metadata" in res
    assert "lineage" in res
    assert "completeness" in res
    assert "blocks" in res

    # Verify blocks
    blocks = res["blocks"]
    assert "MEMORY" in blocks
    assert blocks["MEMORY"]["loaded"] is True
    assert "RELATIONSHIPS" in blocks
    assert blocks["RELATIONSHIPS"]["loaded"] is True
    assert "PROJECTIONS" in blocks


@pytest.mark.asyncio
async def test_7_step_pipeline_organization_and_property_context(
    test_workspace_id: uuid.UUID,
    context_gateway: MemoryContextGateway,
):
    """Verify pipeline handles organization and property context composition."""
    graph_facade = context_gateway._pipeline._graph_facade
    company_id = f"comp-{uuid.uuid4().hex[:8]}"
    prop_id = f"prop-{uuid.uuid4().hex[:8]}"

    # Seed edge Company -> Property
    await graph_facade.commands.create_relationship(
        source=EntityReference(entity_type=GraphNodeType.COMPANY, entity_id=company_id, workspace_id=test_workspace_id),
        target=EntityReference(entity_type=GraphNodeType.PROPERTY, entity_id=prop_id, workspace_id=test_workspace_id),
        relationship_type=RelationshipType.OWNS,
        workspace_id=test_workspace_id,
    )

    # Query Organization context
    org_res = await context_gateway.get_organization_context(
        org_id=company_id,
        workspace_id=test_workspace_id,
    )
    assert org_res["scope"] == "ORGANIZATION"
    assert org_res["entity_id"] == company_id

    # Query Property context
    prop_res = await context_gateway.get_property_context(
        property_id=prop_id,
        workspace_id=test_workspace_id,
    )
    assert prop_res["scope"] == "PROPERTY"
    assert prop_res["entity_id"] == prop_id


@pytest.mark.asyncio
async def test_executive_context_generation(
    test_workspace_id: uuid.UUID,
    context_gateway: MemoryContextGateway,
):
    """Verify workspace executive intelligence context generation."""
    exec_res = await context_gateway.get_executive_context(
        workspace_id=test_workspace_id,
    )
    assert exec_res["scope"] == "EXECUTIVE"
    assert "STATISTICS" in exec_res["blocks"]
    assert exec_res["completeness"]["score"] >= 0.0


@pytest.mark.asyncio
async def test_export_formats_and_structured_context_dto(
    test_workspace_id: uuid.UUID,
    in_memory_read_repo: InMemoryMemoryReadRepository,
    context_gateway: MemoryContextGateway,
):
    """Verify export to Executive DTO, Dashboard DTO, and StructuredContextDTO."""
    customer_id = str(uuid.uuid4())
    mem = CustomerMemory(
        id=uuid.uuid4(),
        customer_id=uuid.UUID(customer_id),
        workspace_id=test_workspace_id,
        version_number=1,
        revision_id=1,
        lifecycle_status=LifecycleStatus.ACTIVE,
        is_deleted=False,
        memory_payload={
            "identity": {"full_name": "Miles Dyson", "primary_email": "dyson@cyberdyne.com"},
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    in_memory_read_repo.add_memory(mem)

    # 1. Executive Export
    exec_export = await context_gateway.export_context(
        scope=ContextScope.CUSTOMER,
        entity_id=customer_id,
        workspace_id=test_workspace_id,
        target_format=ExportTargetFormat.EXECUTIVE,
    )
    assert isinstance(exec_export, ExecutiveContextExportDTO)
    assert exec_export.scope == "CUSTOMER"
    assert "total_relationships" in exec_export.key_metrics

    # 2. Dashboard Export
    dash_export = await context_gateway.export_context(
        scope=ContextScope.CUSTOMER,
        entity_id=customer_id,
        workspace_id=test_workspace_id,
        target_format=ExportTargetFormat.DASHBOARD,
    )
    assert isinstance(dash_export, DashboardContextExportDTO)
    assert len(dash_export.cards) > 0
    assert dash_export.cards[0]["type"] == "PROFILE_CARD"

    # 3. Structured Context DTO Export (General-purpose multi-consumer format)
    struct_export = await context_gateway.export_context(
        scope=ContextScope.CUSTOMER,
        entity_id=customer_id,
        workspace_id=test_workspace_id,
        target_format=ExportTargetFormat.STRUCTURED_CONTEXT,
    )
    assert isinstance(struct_export, StructuredContextDTO)
    assert struct_export.scope == "CUSTOMER"
    assert struct_export.entity_key == f"CUSTOMER:{customer_id}"
    assert struct_export.token_estimate > 0
    assert struct_export.lineage is not None
    assert struct_export.completeness is not None


@pytest.mark.asyncio
async def test_context_cache_contract():
    """Verify AbstractContextCache interface and providers."""
    # NoOp Cache
    noop = NoOpContextCache()
    assert await noop.get("k") is None
    assert await noop.has("k") is False

    # InMemory Cache
    in_mem = InMemoryContextCache()
    assert await in_mem.has("k1") is False

    mock_context = ComposedContext(
        scope=ContextScope.CUSTOMER,
        entity_id="c1",
        workspace_id=None,
        metadata=ContextMetadata(context_id=uuid.uuid4()),
        lineage=ContextLineage(),
        completeness=ContextCompletenessReport(),
    )
    await in_mem.set("k1", mock_context)
    assert await in_mem.has("k1") is True
    retrieved = await in_mem.get("k1")
    assert retrieved is not None
    assert retrieved.entity_id == "c1"

    await in_mem.invalidate("k1")
    assert await in_mem.has("k1") is False


@pytest.mark.asyncio
async def test_frozen_rest_api_endpoints(
    test_workspace_id: uuid.UUID,
    in_memory_read_repo: InMemoryMemoryReadRepository,
    context_gateway: MemoryContextGateway,
):
    """Verify frozen REST endpoints under /api/v1/memory/context."""
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Seed Customer
        cust_id = str(uuid.uuid4())
        mem = CustomerMemory(
            id=uuid.uuid4(),
            customer_id=uuid.UUID(cust_id),
            workspace_id=test_workspace_id,
            version_number=1,
            revision_id=1,
            lifecycle_status=LifecycleStatus.ACTIVE,
            is_deleted=False,
            memory_payload={
                "identity": {"full_name": "John Connor", "primary_email": "john@resistance.org"},
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        in_memory_read_repo.add_memory(mem)

        # 2. GET /api/v1/memory/context/customer/{customer_id}
        resp = await client.get(
            f"/api/v1/memory/context/customer/{cust_id}",
            params={"workspace_id": str(test_workspace_id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scope"] == "CUSTOMER"
        assert data["entity_id"] == cust_id
        assert data["metadata"]["context_id"] is not None

        # 3. GET /api/v1/memory/context/executive
        exec_resp = await client.get(
            "/api/v1/memory/context/executive",
            params={"workspace_id": str(test_workspace_id)},
        )
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        assert exec_data["scope"] == "EXECUTIVE"

        # 4. POST /api/v1/memory/context/custom
        custom_resp = await client.post(
            "/api/v1/memory/context/custom",
            json={
                "entity_type": "PROPERTY",
                "entity_id": "prop-99",
                "workspace_id": str(test_workspace_id),
                "blocks": ["RELATIONSHIPS"],
            },
        )
        assert custom_resp.status_code == 200
        custom_data = custom_resp.json()
        assert custom_data["scope"] == "CUSTOM"
        assert custom_data["entity_id"] == "prop-99"

        # 5. POST /api/v1/memory/context/export (StructuredContextDTO)
        exp_resp = await client.post(
            "/api/v1/memory/context/export",
            params={
                "scope": "CUSTOMER",
                "entity_id": cust_id,
                "workspace_id": str(test_workspace_id),
                "target_format": "STRUCTURED_CONTEXT",
            },
        )
        assert exp_resp.status_code == 200
        exp_data = exp_resp.json()
        assert exp_data["scope"] == "CUSTOMER"
        assert exp_data["entity_key"] == f"CUSTOMER:{cust_id}"
        assert "token_estimate" in exp_data
