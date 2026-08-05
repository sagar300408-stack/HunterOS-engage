"""
HunterOS Engage — Comprehensive Knowledge Graph Test Suite (Phase 2.1.4)

Validates:
  1. NodeRegistry and dynamic handlers
  2. RelationshipAggregate domain lifecycle, invariants, and events
  3. RelationshipValidator (duplicates, cycles, compatibility, workspace isolation)
  4. GraphStorageProvider, WriteRepository & ReadRepository
  5. Pluggable Traversal Strategies (BFS, DFS, ShortestPath, Weighted)
  6. Graph Projection Engine (Customer 360, Organization, Property, Opportunity, Custom)
  7. Graph Statistics and Degree Centrality Metrics
  8. Graph Visualization Serializers (Cytoscape, D3, ReactFlow, Tabular)
  9. CQRS Command/Query Services and KnowledgeGraphFacade
  10. REST API Router Endpoints
"""

import pytest
import uuid
from typing import Any, Dict, List, Optional
from httpx import AsyncClient, ASGITransport

from app.domain.memory.graph.export import GraphExportEngine
from app.domain.memory.graph.facade import KnowledgeGraphFacade
from app.domain.memory.graph.models import (
    CircularRelationshipError,
    CrossWorkspaceRelationshipError,
    DuplicateRelationshipError,
    EntityReference,
    GraphNodeType,
    IncompatibleNodeTypesError,
    RelationshipAggregate,
    RelationshipArchivedEvent,
    RelationshipCreatedEvent,
    RelationshipDeletedEvent,
    RelationshipDirection,
    RelationshipMetadata,
    RelationshipNotFoundError,
    RelationshipRestoredEvent,
    RelationshipStatus,
    RelationshipType,
    RelationshipUpdatedEvent,
    RelationshipValidationError,
)
from app.domain.memory.graph.node_registry import (
    AbstractNodeHandler,
    CustomerNodeHandler,
    NodeRegistry,
    default_node_registry,
)
from app.domain.memory.graph.projections.engine import GraphProjectionEngine
from app.domain.memory.graph.projections.registry import (
    Customer360Projection,
    GraphProjectionRegistry,
    OpportunityNetworkProjection,
    OrganizationProjection,
    PropertyNetworkProjection,
)
from app.domain.memory.graph.repository import (
    GraphReadRepository,
    GraphWriteRepository,
)
from app.domain.memory.graph.router import router, set_graph_facade
from app.domain.memory.graph.schemas import (
    EntityReferenceDTO,
    EntityRelationshipCreateRequest,
    EntityRelationshipUpdateRequest,
    GraphQueryRequest,
    GraphTraversalRequest,
    PathFindingRequest,
    RelationshipBulkCreateRequest,
    TreeTraversalRequest,
)
from app.domain.memory.graph.services import (
    GraphCommandService,
    GraphQueryService,
)
from app.domain.memory.graph.statistics import GraphStatisticsEngine
from app.domain.memory.graph.storage import AbstractGraphStorageProvider
from app.domain.memory.graph.traversal.engine import GraphTraversalEngine
from app.domain.memory.graph.traversal.strategies import (
    BreadthFirstTraversal,
    DepthFirstTraversal,
    ShortestPathTraversal,
    WeightedTraversal,
)
from app.domain.memory.graph.validation import (
    RelationshipValidator,
    default_relationship_validator,
)
from app.main import app


# ── In-Memory Storage Provider for Isolated Unit Testing ─────────────────────

class InMemoryGraphStorageProvider(AbstractGraphStorageProvider):
    """Fast in-memory storage implementation for high-speed deterministic test suite."""

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


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def workspace_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def in_memory_storage() -> InMemoryGraphStorageProvider:
    return InMemoryGraphStorageProvider()


@pytest.fixture
def write_repo(in_memory_storage: InMemoryGraphStorageProvider) -> GraphWriteRepository:
    return GraphWriteRepository(in_memory_storage)


@pytest.fixture
def read_repo(in_memory_storage: InMemoryGraphStorageProvider) -> GraphReadRepository:
    return GraphReadRepository(in_memory_storage)


@pytest.fixture
def facade(write_repo: GraphWriteRepository, read_repo: GraphReadRepository) -> KnowledgeGraphFacade:
    cmd = GraphCommandService(write_repo, read_repo, default_relationship_validator)
    qry = GraphQueryService(read_repo)
    return KnowledgeGraphFacade(
        command_service=cmd,
        query_service=qry,
    )


# ── 1. NodeRegistry Tests ─────────────────────────────────────────────────────

def test_node_registry_handlers():
    reg = NodeRegistry()
    assert reg.is_supported(GraphNodeType.CUSTOMER)
    assert reg.is_supported(GraphNodeType.COMPANY)
    assert reg.is_supported(GraphNodeType.PROPERTY)
    assert reg.is_supported(GraphNodeType.OPPORTUNITY)
    assert reg.is_supported(GraphNodeType.CUSTOM)

    handler = reg.get_handler(GraphNodeType.CUSTOMER)
    assert handler.node_type == GraphNodeType.CUSTOMER

    ref = EntityReference(
        entity_type=GraphNodeType.CUSTOMER,
        entity_id="cust-101",
        label="John Doe",
        properties={"tier": "VIP"},
    )
    handler.validate_reference(ref)
    assert ref.key == "CUSTOMER:cust-101"


def test_node_registry_custom_handler():
    reg = NodeRegistry()

    class VehicleNodeHandler(AbstractNodeHandler):
        @property
        def node_type(self) -> GraphNodeType | str:
            return "VEHICLE"

        def validate_reference(self, reference: EntityReference) -> None:
            if not reference.entity_id:
                raise RelationshipValidationError("Vehicle ID missing")

    reg.register_handler(VehicleNodeHandler())
    assert reg.is_supported("VEHICLE")
    handler = reg.get_handler("VEHICLE")
    assert handler.node_type == "VEHICLE"


# ── 2. RelationshipAggregate & Events Tests ───────────────────────────────────

def test_relationship_aggregate_lifecycle(workspace_id: uuid.UUID):
    src = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="c1", workspace_id=workspace_id)
    tgt = EntityReference(entity_type=GraphNodeType.PROPERTY, entity_id="p1", workspace_id=workspace_id)
    meta = RelationshipMetadata(confidence=0.9, source="CRM")

    agg = RelationshipAggregate.create(
        workspace_id=workspace_id,
        source=src,
        target=tgt,
        relationship_type=RelationshipType.INTERESTED_IN,
        strength=0.8,
        metadata=meta,
    )

    assert agg.status == RelationshipStatus.ACTIVE
    assert agg.version == 1
    assert not agg.is_deleted
    assert len(agg.events) == 1
    assert isinstance(agg.events[0], RelationshipCreatedEvent)

    # Update
    agg.update(strength=0.95, metadata_update={"notes": "Highly interested"}, confidence=0.99)
    assert agg.strength == 0.95
    assert agg.metadata.confidence == 0.99
    assert agg.metadata.custom_attributes["notes"] == "Highly interested"
    assert agg.version == 2
    assert isinstance(agg.events[-1], RelationshipUpdatedEvent)

    # Archive
    agg.archive(reason="Deal closed", actor="admin")
    assert agg.status == RelationshipStatus.ARCHIVED
    assert agg.version == 3
    assert isinstance(agg.events[-1], RelationshipArchivedEvent)

    # Soft Delete
    agg.delete(reason="User request", actor="admin")
    assert agg.is_deleted is True
    assert agg.version == 4
    assert isinstance(agg.events[-1], RelationshipDeletedEvent)

    # Restore
    agg.restore(actor="admin")
    assert agg.is_deleted is False
    assert agg.status == RelationshipStatus.ACTIVE
    assert agg.version == 5
    assert isinstance(agg.events[-1], RelationshipRestoredEvent)

    collected = agg.collect_events()
    assert len(collected) == 5
    assert len(agg.events) == 0


# ── 3. RelationshipValidator Tests ───────────────────────────────────────────

def test_validator_self_loop_prevention(workspace_id: uuid.UUID):
    v = RelationshipValidator()
    src = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="c1", workspace_id=workspace_id)
    tgt = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="c1", workspace_id=workspace_id)

    with pytest.raises(RelationshipValidationError, match="Self-referential relationship is not allowed"):
        v.validate_relationship(source=src, target=tgt, relationship_type=RelationshipType.KNOWS)


def test_validator_cross_workspace_prevention():
    v = RelationshipValidator()
    ws1 = uuid.uuid4()
    ws2 = uuid.uuid4()
    src = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="c1", workspace_id=ws1)
    tgt = EntityReference(entity_type=GraphNodeType.COMPANY, entity_id="comp1", workspace_id=ws2)

    with pytest.raises(CrossWorkspaceRelationshipError):
        v.validate_relationship(source=src, target=tgt, relationship_type=RelationshipType.WORKS_FOR)


def test_validator_duplicate_prevention(workspace_id: uuid.UUID):
    v = RelationshipValidator()
    src = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="c1", workspace_id=workspace_id)
    tgt = EntityReference(entity_type=GraphNodeType.COMPANY, entity_id="comp1", workspace_id=workspace_id)

    existing = [
        {
            "source_key": "CUSTOMER:c1",
            "target_key": "COMPANY:comp1",
            "relationship_type": "WORKS_FOR",
            "is_deleted": False,
            "status": "ACTIVE",
        }
    ]

    with pytest.raises(DuplicateRelationshipError):
        v.validate_relationship(
            source=src,
            target=tgt,
            relationship_type=RelationshipType.WORKS_FOR,
            existing_edges=existing,
        )


def test_validator_incompatible_types(workspace_id: uuid.UUID):
    v = RelationshipValidator()
    src = EntityReference(entity_type=GraphNodeType.PROPERTY, entity_id="p1", workspace_id=workspace_id)
    tgt = EntityReference(entity_type=GraphNodeType.DOCUMENT, entity_id="d1", workspace_id=workspace_id)

    with pytest.raises(IncompatibleNodeTypesError):
        v.validate_relationship(
            source=src,
            target=tgt,
            relationship_type=RelationshipType.WORKS_FOR,
        )


def test_validator_cycle_prevention(workspace_id: uuid.UUID):
    v = RelationshipValidator()
    # A -> B -> C -> A
    a = EntityReference(entity_type=GraphNodeType.EMPLOYEE, entity_id="A", workspace_id=workspace_id)
    b = EntityReference(entity_type=GraphNodeType.EMPLOYEE, entity_id="B", workspace_id=workspace_id)
    c = EntityReference(entity_type=GraphNodeType.EMPLOYEE, entity_id="C", workspace_id=workspace_id)

    existing = [
        {"source_key": "EMPLOYEE:A", "target_key": "EMPLOYEE:B", "relationship_type": "MANAGES", "is_deleted": False, "status": "ACTIVE"},
        {"source_key": "EMPLOYEE:B", "target_key": "EMPLOYEE:C", "relationship_type": "MANAGES", "is_deleted": False, "status": "ACTIVE"},
    ]

    # Attempting C -> A forms a cycle
    with pytest.raises(CircularRelationshipError):
        v.validate_relationship(
            source=c,
            target=a,
            relationship_type=RelationshipType.MANAGES,
            existing_edges=existing,
        )


# ── 4. GraphStorage and Repositories Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_write_and_read_repositories(write_repo: GraphWriteRepository, read_repo: GraphReadRepository, workspace_id: uuid.UUID):
    src = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="c1", workspace_id=workspace_id)
    tgt = EntityReference(entity_type=GraphNodeType.COMPANY, entity_id="acme", workspace_id=workspace_id)

    agg = RelationshipAggregate.create(
        workspace_id=workspace_id,
        source=src,
        target=tgt,
        relationship_type=RelationshipType.WORKS_FOR,
    )

    saved = await write_repo.save(agg)
    assert saved.id == agg.id

    fetched = await read_repo.get_by_id(agg.id)
    assert fetched is not None
    assert fetched.source.key == "CUSTOMER:c1"
    assert fetched.target.key == "COMPANY:acme"

    # Query
    queried = await read_repo.query(workspace_id=workspace_id, relationship_types=["WORKS_FOR"])
    assert len(queried) == 1

    # Incidents
    incidents = await read_repo.get_incident_edges(workspace_id=workspace_id, entity_type="CUSTOMER", entity_id="c1")
    assert len(incidents) == 1

    # Archive via write repo
    archived = await write_repo.archive(agg.id, reason="Left company")
    assert archived.status == RelationshipStatus.ARCHIVED

    # Query active edges should now be empty
    active = await read_repo.get_all_active_edges_for_workspace(workspace_id=workspace_id)
    assert len(active) == 0


# ── 5. Traversal Strategies Tests ─────────────────────────────────────────────

def test_traversal_strategies(workspace_id: uuid.UUID):
    # Setup graph: N1 -> N2 -> N3 -> N4, N1 -> N3
    n1 = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="1", workspace_id=workspace_id)
    n2 = EntityReference(entity_type=GraphNodeType.CONTACT, entity_id="2", workspace_id=workspace_id)
    n3 = EntityReference(entity_type=GraphNodeType.COMPANY, entity_id="3", workspace_id=workspace_id)
    n4 = EntityReference(entity_type=GraphNodeType.PROPERTY, entity_id="4", workspace_id=workspace_id)

    e1 = RelationshipAggregate.create(workspace_id, n1, n2, RelationshipType.KNOWS, strength=0.5)
    e2 = RelationshipAggregate.create(workspace_id, n2, n3, RelationshipType.WORKS_FOR, strength=0.5)
    e3 = RelationshipAggregate.create(workspace_id, n3, n4, RelationshipType.OWNS, strength=0.9)
    e4 = RelationshipAggregate.create(workspace_id, n1, n3, RelationshipType.INTERESTED_IN, strength=0.95)

    edges = [e1, e2, e3, e4]

    # BFS Traversal from N1
    bfs = BreadthFirstTraversal()
    res_bfs = bfs.execute(edges, start_key="CUSTOMER:1", max_depth=2)
    assert len(res_bfs.nodes) >= 3
    assert "CUSTOMER:1" in res_bfs.depths
    assert res_bfs.depths["CUSTOMER:1"] == 0

    # DFS Traversal from N1
    dfs = DepthFirstTraversal()
    res_dfs = dfs.execute(edges, start_key="CUSTOMER:1", max_depth=3)
    assert len(res_dfs.nodes) == 4

    # Shortest Path N1 -> N4
    sp = ShortestPathTraversal()
    res_sp = sp.execute(edges, start_key="CUSTOMER:1", target_key="PROPERTY:4", max_depth=5)
    assert len(res_sp.edges) == 2  # N1 -> N3 -> N4 is 2 hops, whereas N1 -> N2 -> N3 -> N4 is 3 hops
    assert res_sp.edges[0].source.key == "CUSTOMER:1"
    assert res_sp.edges[0].target.key == "COMPANY:3"
    assert res_sp.edges[1].target.key == "PROPERTY:4"

    # Weighted Traversal (Dijkstra) N1 -> N4
    dijkstra = WeightedTraversal()
    res_weighted = dijkstra.execute(edges, start_key="CUSTOMER:1", target_key="PROPERTY:4", max_depth=5)
    assert len(res_weighted.edges) == 2
    assert res_weighted.total_cost > 0


# ── 6. Graph Projections Tests ────────────────────────────────────────────────

def test_projections(workspace_id: uuid.UUID):
    cust = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="c1", label="Alice", workspace_id=workspace_id)
    comp = EntityReference(entity_type=GraphNodeType.COMPANY, entity_id="co1", label="Acme Corp", workspace_id=workspace_id)
    prop = EntityReference(entity_type=GraphNodeType.PROPERTY, entity_id="p1", label="Sunset Villa", workspace_id=workspace_id)
    opp = EntityReference(entity_type=GraphNodeType.OPPORTUNITY, entity_id="o1", label="Villa Deal", workspace_id=workspace_id)
    agent = EntityReference(entity_type=GraphNodeType.EMPLOYEE, entity_id="e1", label="Bob Agent", workspace_id=workspace_id)

    e1 = RelationshipAggregate.create(workspace_id, cust, comp, RelationshipType.WORKS_FOR)
    e2 = RelationshipAggregate.create(workspace_id, cust, prop, RelationshipType.INTERESTED_IN)
    e3 = RelationshipAggregate.create(workspace_id, cust, opp, RelationshipType.DECISION_MAKER_FOR)
    e4 = RelationshipAggregate.create(workspace_id, comp, agent, RelationshipType.MANAGES)
    e5 = RelationshipAggregate.create(workspace_id, agent, prop, RelationshipType.MANAGES)

    edges = [e1, e2, e3, e4, e5]

    # Customer 360 Projection
    c360 = Customer360Projection()
    res_c360 = c360.project(edges, cust)
    assert res_c360.customer.entity_id == "c1"
    assert len(res_c360.companies) == 1
    assert len(res_c360.properties) == 1
    assert len(res_c360.opportunities) == 1
    assert res_c360.total_connections == 3

    # Organization Projection
    org_proj = OrganizationProjection()
    res_org = org_proj.project(edges, comp)
    assert res_org.company.entity_id == "co1"
    assert len(res_org.employees) == 1

    # Property Network Projection
    prop_proj = PropertyNetworkProjection()
    res_prop = prop_proj.project(edges, prop)
    assert res_prop.property_entity.entity_id == "p1"
    assert len(res_prop.interested_prospects) == 1
    assert len(res_prop.managing_agents) == 1


# ── 7. Graph Statistics and Centrality Tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_graph_statistics(write_repo: GraphWriteRepository, read_repo: GraphReadRepository, workspace_id: uuid.UUID):
    c1 = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="1", workspace_id=workspace_id)
    c2 = EntityReference(entity_type=GraphNodeType.COMPANY, entity_id="2", workspace_id=workspace_id)
    c3 = EntityReference(entity_type=GraphNodeType.PROPERTY, entity_id="3", workspace_id=workspace_id)

    e1 = RelationshipAggregate.create(workspace_id, c1, c2, RelationshipType.WORKS_FOR, strength=0.85, metadata=RelationshipMetadata(confidence=0.95))
    e2 = RelationshipAggregate.create(workspace_id, c1, c3, RelationshipType.OWNS, strength=0.5, metadata=RelationshipMetadata(confidence=0.8))

    await write_repo.save(e1)
    await write_repo.save(e2)

    stats_engine = GraphStatisticsEngine(read_repo)
    stats = await stats_engine.compute_statistics(workspace_id)

    assert stats.total_nodes == 3
    assert stats.total_relationships == 2
    assert stats.active_relationships == 2
    assert stats.graph_density > 0
    assert stats.relationship_type_distribution["WORKS_FOR"] == 1
    assert stats.relationship_type_distribution["OWNS"] == 1
    assert stats.relationship_strength_distribution["0.8-1.0"] == 1
    assert "CUSTOMER:1" in stats.node_centrality_metrics
    assert stats.node_centrality_metrics["CUSTOMER:1"] == 1.0  # connected to both nodes


# ── 8. Visualization Exports Tests ───────────────────────────────────────────

def test_visualization_exports(workspace_id: uuid.UUID):
    n1 = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="1", label="Alice", workspace_id=workspace_id)
    n2 = EntityReference(entity_type=GraphNodeType.COMPANY, entity_id="2", label="Acme", workspace_id=workspace_id)
    edge = RelationshipAggregate.create(workspace_id, n1, n2, RelationshipType.WORKS_FOR)
    edges = [edge]

    # Cytoscape
    cyto = GraphExportEngine.export_cytoscape(edges)
    assert cyto.format == "cytoscape"
    assert len(cyto.nodes) == 2
    assert len(cyto.edges) == 1
    assert "data" in cyto.nodes[0]

    # D3
    d3 = GraphExportEngine.export_d3(edges)
    assert d3.format == "d3"
    assert len(d3.nodes) == 2
    assert len(d3.edges) == 1
    assert "group" in d3.nodes[0]

    # ReactFlow
    rf = GraphExportEngine.export_reactflow(edges)
    assert rf.format == "reactflow"
    assert len(rf.nodes) == 2
    assert "position" in rf.nodes[0]

    # Tabular
    tab = GraphExportEngine.export_tabular(edges)
    assert len(tab) == 1
    assert tab[0]["source_type"] == "CUSTOMER"
    assert tab[0]["target_type"] == "COMPANY"


# ── 9. CQRS & Facade Integration Tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_facade_end_to_end(facade: KnowledgeGraphFacade, workspace_id: uuid.UUID):
    src = EntityReference(entity_type=GraphNodeType.CUSTOMER, entity_id="cust-99", workspace_id=workspace_id)
    tgt = EntityReference(entity_type=GraphNodeType.PROPERTY, entity_id="prop-99", workspace_id=workspace_id)

    # 1. Create
    created = await facade.create_relationship(
        source=src,
        target=tgt,
        relationship_type=RelationshipType.INTERESTED_IN,
        strength=0.9,
        workspace_id=workspace_id,
    )
    assert created.id is not None
    assert created.version == 1

    # 2. Get
    fetched = await facade.get_relationship(created.id)
    assert fetched is not None
    assert fetched.strength == 0.9

    # 3. Update
    updated = await facade.update_relationship(created.id, strength=0.95, metadata_update={"budget": 1000000})
    assert updated.strength == 0.95
    assert updated.version == 2

    # 4. Query
    rels = await facade.query_relationships(workspace_id=workspace_id, relationship_types=[RelationshipType.INTERESTED_IN])
    assert len(rels) == 1

    # 5. Direct
    direct = await facade.get_direct_relationships(workspace_id=workspace_id, entity_type=GraphNodeType.CUSTOMER, entity_id="cust-99")
    assert len(direct) == 1

    # 6. Tree
    tree = await facade.build_relationship_tree(workspace_id=workspace_id, root_entity_type=GraphNodeType.CUSTOMER, root_entity_id="cust-99")
    assert tree.node.entity_id == "cust-99"
    assert len(tree.children) == 1
    assert tree.children[0].node.entity_id == "prop-99"

    # 7. Customer 360
    c360 = await facade.project_customer_360(workspace_id=workspace_id, customer_id="cust-99")
    assert len(c360.properties) == 1

    # 8. Delete & Restore
    deleted = await facade.delete_relationship(created.id, reason="Archived lead")
    assert deleted.is_deleted is True

    restored = await facade.restore_relationship(created.id)
    assert restored.is_deleted is False


# ── 10. REST API Endpoints Tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rest_api_endpoints(facade: KnowledgeGraphFacade, workspace_id: uuid.UUID):
    set_graph_facade(facade)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create relationship
        payload = {
            "source": {"entity_type": "CUSTOMER", "entity_id": "api-c1", "workspace_id": str(workspace_id)},
            "target": {"entity_type": "COMPANY", "entity_id": "api-comp1", "workspace_id": str(workspace_id)},
            "relationship_type": "WORKS_FOR",
            "direction": "DIRECTED",
            "strength": 0.88,
            "workspace_id": str(workspace_id),
        }
        res = await client.post("/api/v1/memory/graph/relationships", json=payload)
        assert res.status_code == 201
        data = res.json()
        rel_id = data["relationship_id"]
        assert data["relationship_type"] == "WORKS_FOR"

        # Get relationship
        res = await client.get(f"/api/v1/memory/graph/relationships/{rel_id}")
        assert res.status_code == 200
        assert res.json()["relationship_id"] == rel_id

        # Direct relationships
        res = await client.get(f"/api/v1/memory/graph/direct?entity_type=CUSTOMER&entity_id=api-c1&workspace_id={workspace_id}")
        assert res.status_code == 200
        assert len(res.json()) == 1

        # Query relationships
        query_payload = {
            "workspace_id": str(workspace_id),
            "entity_type": "CUSTOMER",
            "entity_id": "api-c1",
        }
        res = await client.post("/api/v1/memory/graph/query", json=query_payload)
        assert res.status_code == 200
        assert len(res.json()) == 1

        # Customer 360 projection
        res = await client.get(f"/api/v1/memory/graph/projections/customer-360/api-c1?workspace_id={workspace_id}")
        assert res.status_code == 200
        assert res.json()["customer"]["entity_id"] == "api-c1"
        assert len(res.json()["companies"]) == 1

        # Statistics
        res = await client.get(f"/api/v1/memory/graph/statistics?workspace_id={workspace_id}")
        assert res.status_code == 200
        assert res.json()["total_nodes"] == 2
        assert res.json()["total_relationships"] == 1

        # Export
        res = await client.get(f"/api/v1/memory/graph/export?workspace_id={workspace_id}&format=cytoscape")
        assert res.status_code == 200
        assert res.json()["format"] == "cytoscape"
        assert len(res.json()["nodes"]) == 2
