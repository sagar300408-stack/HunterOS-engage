"""
BW4 Certification Test — B5 (Knowledge Graph Traversal & Context Expansion)

Tests run against real PostgreSQL.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone

# ── Bootstrap SQLAlchemy mapper order ─────────────────────────────────────────
from app.domain.customers.models import Customer  # noqa: F401 — must be first
from app.domain.conversations.models import Conversation  # noqa: F401
from app.domain.memory.graph.models import (
    EntityReference,
    EntityRelationship,
    GraphNodeType,
    RelationshipAggregate,
    RelationshipDirection,
    RelationshipStatus,
    RelationshipType,
)
from app.domain.memory.graph.storage import SqlAlchemyGraphStorageProvider
from app.domain.memory.graph.repository import GraphReadRepository, GraphWriteRepository
from app.domain.memory.graph.traversal.engine import GraphTraversalEngine
from app.domain.memory.graph.facade import KnowledgeGraphFacade
from app.domain.memory.intelligence.pipeline import ContextPipeline
from app.domain.memory.intelligence.models import (
    ContextBlockType,
    ContextScope,
)
from app.domain.memory.intelligence.schemas import ContextRequestOptions


@pytest_asyncio.fixture
async def pg_session_graph(pg_engine):
    from app.domain.conversations.models import Base
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


def _create_relationship_orm(
    workspace_id: uuid.UUID,
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
    rel_type: str,
    strength: float = 1.0,
    confidence: float = 1.0,
) -> EntityRelationship:
    return EntityRelationship(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        relationship_type=rel_type,
        source_node_type=source_type,
        source_node_id=source_id,
        target_node_type=target_type,
        target_node_id=target_id,
        direction=RelationshipDirection.DIRECTED.value,
        strength=strength,
        confidence=confidence,
        status=RelationshipStatus.ACTIVE.value,
        is_deleted=False,
    )


@pytest.mark.asyncio
async def test_b5_multi_hop_graph_traversal_bfs(pg_session_graph):
    """
    B5 Knowledge Graph Traversal:
    Create a 3-hop chain:
      Customer(c1) -> (WORKS_FOR) -> Company(org1) -> (OWNS) -> Property(prop1) -> (RELATED_TO) -> Location(loc1)
    Traverse with depth=3 starting from Customer(c1).
    Assert: all 3 hops are discovered and correctly ordered by depth.
    """
    session = pg_session_graph
    workspace_id = uuid.uuid4()

    c1_id = f"cust_{uuid.uuid4().hex[:8]}"
    org1_id = f"company_{uuid.uuid4().hex[:8]}"
    prop1_id = f"prop_{uuid.uuid4().hex[:8]}"
    loc1_id = f"loc_{uuid.uuid4().hex[:8]}"

    # Insert 3 chained edges
    edge1 = _create_relationship_orm(workspace_id, "CUSTOMER", c1_id, "COMPANY", org1_id, "WORKS_FOR")
    edge2 = _create_relationship_orm(workspace_id, "COMPANY", org1_id, "PROPERTY", prop1_id, "OWNS")
    edge3 = _create_relationship_orm(workspace_id, "PROPERTY", prop1_id, "CUSTOM", loc1_id, "RELATED_TO")

    session.add_all([edge1, edge2, edge3])
    await session.flush()

    storage = SqlAlchemyGraphStorageProvider(session_factory=lambda: session)
    read_repo = GraphReadRepository(storage)
    engine = GraphTraversalEngine(read_repo)

    # 1. Traverse 1 hop (reaches start node + 1 neighbor org1)
    t1 = await engine.traverse_neighbors(
        workspace_id=workspace_id,
        start_entity_type="CUSTOMER",
        start_entity_id=c1_id,
        max_depth=1,
        strategy_name="bfs",
        session=session,
    )
    neighbor_ids_1 = {n.entity_id for n in t1.nodes if n.entity_id != c1_id}
    assert neighbor_ids_1 == {org1_id}
    assert len(t1.edges) == 1

    # 2. Traverse 2 hops (reaches start node + org1, prop1)
    t2 = await engine.traverse_neighbors(
        workspace_id=workspace_id,
        start_entity_type="CUSTOMER",
        start_entity_id=c1_id,
        max_depth=2,
        strategy_name="bfs",
        session=session,
    )
    neighbor_ids_2 = {n.entity_id for n in t2.nodes if n.entity_id != c1_id}
    assert neighbor_ids_2 == {org1_id, prop1_id}
    assert len(t2.edges) == 2

    # 3. Traverse 3 hops (reaches start node + org1, prop1, loc1)
    t3 = await engine.traverse_neighbors(
        workspace_id=workspace_id,
        start_entity_type="CUSTOMER",
        start_entity_id=c1_id,
        max_depth=3,
        strategy_name="bfs",
        session=session,
    )
    neighbor_ids_3 = {n.entity_id for n in t3.nodes if n.entity_id != c1_id}
    assert neighbor_ids_3 == {org1_id, prop1_id, loc1_id}
    assert len(t3.edges) == 3
    assert t3.depths.get(f"COMPANY:{org1_id}") == 1
    assert t3.depths.get(f"PROPERTY:{prop1_id}") == 2
    assert t3.depths.get(f"CUSTOM:{loc1_id}") == 3


@pytest.mark.asyncio
async def test_b5_graph_traversal_workspace_isolation(pg_session_graph):
    """
    B5 Multi-Tenant Workspace Isolation:
    Workspace A has: Node A1 -> Node A2
    Workspace B has: Node B1 -> Node B2
    Traversing in Workspace A starting at Node A1 must NEVER return Node B1 or Node B2.
    """
    session = pg_session_graph
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()

    a1 = f"cust_a_{uuid.uuid4().hex[:6]}"
    a2 = f"company_a_{uuid.uuid4().hex[:6]}"
    b1 = f"cust_b_{uuid.uuid4().hex[:6]}"
    b2 = f"company_b_{uuid.uuid4().hex[:6]}"

    edge_a = _create_relationship_orm(ws_a, "CUSTOMER", a1, "COMPANY", a2, "WORKS_FOR")
    edge_b = _create_relationship_orm(ws_b, "CUSTOMER", b1, "COMPANY", b2, "WORKS_FOR")

    session.add_all([edge_a, edge_b])
    await session.flush()

    storage = SqlAlchemyGraphStorageProvider(session_factory=lambda: session)
    read_repo = GraphReadRepository(storage)
    engine = GraphTraversalEngine(read_repo)

    result_a = await engine.traverse_neighbors(
        workspace_id=ws_a,
        start_entity_type="CUSTOMER",
        start_entity_id=a1,
        max_depth=2,
        strategy_name="bfs",
        session=session,
    )

    node_ids = {n.entity_id for n in result_a.nodes}
    assert a2 in node_ids
    assert b1 not in node_ids
    assert b2 not in node_ids


@pytest.mark.asyncio
async def test_b5_pipeline_multi_hop_context_injection(pg_session_graph):
    """
    B5 Pipeline Integration:
    Verify that ContextPipeline with max_graph_depth > 1 traverses the graph
    and injects the multi-hop relationships and projection metadata into the ComposedContext.
    """
    session = pg_session_graph
    workspace_id = uuid.uuid4()

    cust_id = f"cust_{uuid.uuid4().hex[:8]}"
    company_id = f"comp_{uuid.uuid4().hex[:8]}"
    prop_id = f"prop_{uuid.uuid4().hex[:8]}"

    # Insert 2-hop graph
    e1 = _create_relationship_orm(workspace_id, "CUSTOMER", cust_id, "COMPANY", company_id, "WORKS_FOR")
    e2 = _create_relationship_orm(workspace_id, "COMPANY", company_id, "PROPERTY", prop_id, "OWNS")
    session.add_all([e1, e2])
    await session.flush()

    storage = SqlAlchemyGraphStorageProvider(session_factory=lambda: session)
    facade = KnowledgeGraphFacade(storage_provider=storage)

    # Initialize Pipeline with real graph facade
    pipeline = ContextPipeline(
        knowledge_graph_facade=facade,
    )

    # Execute pipeline requesting RELATIONSHIPS and PROJECTIONS blocks with depth=2
    options = ContextRequestOptions(
        blocks=["RELATIONSHIPS", "PROJECTIONS"],
        max_graph_depth=2,
    )
    result = await pipeline.execute(
        scope=ContextScope.CUSTOMER,
        entity_id=cust_id,
        workspace_id=workspace_id,
        options=options,
        custom_entity_type="CUSTOMER",
    )

    # 1. MultiHopExpansion should be recorded in projections_applied lineage
    lineage = result.get("lineage", {})
    projections = lineage.get("projections_applied", [])
    assert any("MultiHopExpansion(depth=2)" in p for p in projections), (
        f"MultiHopExpansion missing from lineage: {projections}"
    )

    # 2. RELATIONSHIPS block should contain both hops (e1 and e2)
    blocks = result.get("blocks", {})
    rel_block = blocks.get("RELATIONSHIPS", {})
    assert rel_block.get("loaded") is True
    items = rel_block.get("data", {}).get("items", [])
    assert len(items) >= 2, (
        f"Expected at least 2 multi-hop edges in RELATIONSHIPS block, got {items}"
    )

    # 3. PROJECTIONS block should include the graph traversal metadata
    proj_block = blocks.get("PROJECTIONS", {})
    assert proj_block.get("loaded") is True
    assert "graph_traversal" in proj_block.get("data", {})
    gt_data = proj_block["data"]["graph_traversal"]
    assert gt_data["depth"] == 2
    assert gt_data["total_nodes"] >= 2
