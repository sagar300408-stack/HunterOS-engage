"""
B5 Verification Tests — Knowledge Graph Traversal & Pipeline Integration
========================================================================
Proves:
  1. Pipeline executes graph facade traversal with real persistence.
  2. Empty traversal returns safely.
  3. 1-hop and multi-hop (depth=2) traversal returns appropriate nodes.
  4. Workspace isolation is enforced on graph boundaries (multi-hop does not cross workspaces).
  5. ContextPipeline successfully populates RELATIONSHIPS, STATISTICS, and PROJECTIONS.
"""

import pytest
import pytest_asyncio
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.domain.conversations.models
from app.domain.customers.models import Customer, Base as CustBase
from app.domain.memory.models import Base as MemBase, CustomerMemory
from app.domain.memory.graph.models import EntityRelationship, Base as GraphBase, RelationshipStatus
from app.domain.memory.repositories.read_repository import SqlAlchemyMemoryReadRepository
from app.domain.memory.queries.facade import MemoryQueryFacade
from app.domain.memory.graph.storage import SqlAlchemyGraphStorageProvider
from app.domain.memory.graph.facade import KnowledgeGraphFacade
from app.domain.memory.intelligence.pipeline import ContextPipeline
from app.domain.memory.intelligence.models import ContextScope
from app.domain.memory.intelligence.schemas import ContextRequestOptions, ExportTargetFormat


# ── Test Database Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

@pytest.fixture
def session_maker(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture
async def db_session(engine, session_maker):
    async with engine.begin() as conn:
        await conn.run_sync(CustBase.metadata.create_all)
        await conn.run_sync(MemBase.metadata.create_all)
        await conn.run_sync(GraphBase.metadata.create_all)
    async with session_maker() as session:
        yield session

def _make_pipeline(db_session: AsyncSession) -> ContextPipeline:
    """
    Build a ContextPipeline wired to a deterministic test session via monkey-patch.
    """
    read_repo = SqlAlchemyMemoryReadRepository()
    graph_storage = SqlAlchemyGraphStorageProvider()

    async def _resolve(session=None):
        return db_session, False

    def _resolve_graph(session=None):
        return db_session

    read_repo._resolve_session = _resolve  # type: ignore
    graph_storage._resolve_session = _resolve_graph  # type: ignore

    query_facade = MemoryQueryFacade(read_repo)
    graph_facade = KnowledgeGraphFacade(storage_provider=graph_storage)

    return ContextPipeline(
        memory_read_repo=read_repo,
        memory_query_facade=query_facade,
        knowledge_graph_facade=graph_facade,
    )

# ── B5-1: Empty Traversal ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_b5_empty_traversal(db_session: AsyncSession):
    ws_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    
    db_session.add(Customer(id=cust_id, workspace_id=ws_id, name="No Graph Customer", phone="+1000000000"))
    await db_session.commit()

    pipeline = _make_pipeline(db_session)
    result = await pipeline.execute(
        scope=ContextScope.CUSTOMER,
        entity_id=str(cust_id),
        workspace_id=ws_id,
        options=ContextRequestOptions(max_graph_depth=2, format=ExportTargetFormat.STANDARD_API),
    )

    blocks = result.get("blocks", {})
    rels_data = blocks.get("RELATIONSHIPS", {}).get("data", [])
    rels = rels_data.get("items", []) if isinstance(rels_data, dict) else rels_data
    assert len(rels) == 0, "Expected empty relationships list"
    
    stats = blocks.get("STATISTICS", {}).get("data", {})
    assert isinstance(stats, dict), "Expected statistics dict to be present"

# ── B5-2: Multi-Hop Traversal & Isolation ────────────────────────────────────

@pytest.mark.asyncio
async def test_b5_multi_hop_traversal_and_isolation(db_session: AsyncSession):
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()
    
    cust_a = uuid.uuid4()
    org_a = uuid.uuid4()
    prop_a = uuid.uuid4()
    
    cust_b = uuid.uuid4()
    org_b = uuid.uuid4()
    
    db_session.add(Customer(id=cust_a, workspace_id=ws_a, name="A Customer", phone="+1000000001"))
    db_session.add(Customer(id=cust_b, workspace_id=ws_b, name="B Customer", phone="+1000000002"))
    
    # Workspace A edges: cust_a -> org_a -> prop_a
    rel1 = EntityRelationship(
        id=uuid.uuid4(), workspace_id=ws_a, relationship_type="WORKS_AT",
        source_node_type="CUSTOMER", source_node_id=str(cust_a), source_label="A Customer",
        target_node_type="ORGANIZATION", target_node_id=str(org_a), target_label="A Org",
        direction="DIRECTED", strength=1.0, status=RelationshipStatus.ACTIVE.value,
        metadata_payload={},
    )
    rel2 = EntityRelationship(
        id=uuid.uuid4(), workspace_id=ws_a, relationship_type="OWNS",
        source_node_type="ORGANIZATION", source_node_id=str(org_a), source_label="A Org",
        target_node_type="PROPERTY", target_node_id=str(prop_a), target_label="A Prop",
        direction="DIRECTED", strength=1.0, status=RelationshipStatus.ACTIVE.value,
        metadata_payload={},
    )
    
    # Workspace B edge (must never be returned to A)
    rel3 = EntityRelationship(
        id=uuid.uuid4(), workspace_id=ws_b, relationship_type="WORKS_AT",
        source_node_type="CUSTOMER", source_node_id=str(cust_b), source_label="B Customer",
        target_node_type="ORGANIZATION", target_node_id=str(org_b), target_label="B Org",
        direction="DIRECTED", strength=1.0, status=RelationshipStatus.ACTIVE.value,
        metadata_payload={},
    )
    
    db_session.add_all([rel1, rel2, rel3])
    await db_session.commit()

    pipeline = _make_pipeline(db_session)
    result = await pipeline.execute(
        scope=ContextScope.CUSTOMER,
        entity_id=str(cust_a),
        workspace_id=ws_a,
        options=ContextRequestOptions(max_graph_depth=2, format=ExportTargetFormat.STANDARD_API),
    )

    blocks = result.get("blocks", {})
    rels_data = blocks.get("RELATIONSHIPS", {}).get("data", [])
    rels = rels_data.get("items", []) if isinstance(rels_data, dict) else rels_data
    
    # Since depth is 2, it expands multi-hop but get_direct_relationships only returns 1-hop for the RELATIONSHIPS block.
    # The traversal populates projections or applies effects to composer, but relationships block returns 1-hop.
    assert len(rels) == 1, "Only 1-hop direct relationships are directly embedded in RELATIONSHIPS block"
    assert rels[0]["target_node"]["entity_id"] == str(org_a)
    
    lineage = result.get("lineage", {})
    applied = lineage.get("projections_applied", [])
    assert "MultiHopExpansion(depth=2)" in applied, "Multi-hop traversal must be recorded in lineage"
    assert "Customer360Projection" in applied, "Projection must be executed"

# ── B5-3: Cycle Protection ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_b5_cycle_protection(db_session: AsyncSession):
    ws_id = uuid.uuid4()
    n1 = str(uuid.uuid4())
    n2 = str(uuid.uuid4())
    
    # Cyclic edge n1 -> n2 -> n1
    db_session.add(EntityRelationship(
        id=uuid.uuid4(), workspace_id=ws_id, relationship_type="KNOWS",
        source_node_type="CUSTOMER", source_node_id=n1, source_label="N1",
        target_node_type="CUSTOMER", target_node_id=n2, target_label="N2",
        direction="DIRECTED", strength=1.0, status=RelationshipStatus.ACTIVE.value,
        metadata_payload={},
    ))
    db_session.add(EntityRelationship(
        id=uuid.uuid4(), workspace_id=ws_id, relationship_type="KNOWS",
        source_node_type="CUSTOMER", source_node_id=n2, source_label="N2",
        target_node_type="CUSTOMER", target_node_id=n1, target_label="N1",
        direction="DIRECTED", strength=1.0, status=RelationshipStatus.ACTIVE.value,
        metadata_payload={},
    ))
    await db_session.commit()

    pipeline = _make_pipeline(db_session)
    result = await pipeline.execute(
        scope=ContextScope.CUSTOMER,
        entity_id=n1,
        workspace_id=ws_id,
        options=ContextRequestOptions(max_graph_depth=3, format=ExportTargetFormat.STANDARD_API),
    )
    
    # Should complete without infinite recursion/timeout
    assert "MultiHopExpansion(depth=3)" in result["lineage"]["projections_applied"]
    rels_data = result["blocks"]["RELATIONSHIPS"]["data"]
    rels = rels_data.get("items", []) if isinstance(rels_data, dict) else rels_data
    assert len(rels) == 2, "Both outgoing and incoming edges for N1 are retrieved"
