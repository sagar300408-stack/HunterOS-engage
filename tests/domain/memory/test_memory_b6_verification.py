"""
B6 Verification Tests — Intent Failure Handling
===============================================
Proves explicit failure taxonomy handling:
1. MISSING_REQUIRED_CONTEXT -> deterministic degraded/empty context
2. INVALID_ENTITY_REFERENCE -> HTTP 422 (FastAPI integration test)
3. CONTEXT_RETRIEVAL_FAILURE -> degraded context + diagnostic
4. GRAPH_TRAVERSAL_FAILURE -> degraded context + diagnostic
5. PROJECTION_FAILURE -> degraded context + diagnostic
6. SAFE_EMPTY_CONTEXT -> valid structured empty context
7. WORKSPACE_AUTHORIZATION_FAILURE -> FAIL CLOSED
"""

import pytest
import pytest_asyncio
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
import app.domain.conversations.models
from app.domain.customers.models import Customer, Base as CustBase
from app.domain.memory.models import Base as MemBase, CustomerMemory
from app.domain.memory.graph.models import EntityRelationship, Base as GraphBase, RelationshipStatus
from app.domain.memory.repositories.read_repository import SqlAlchemyMemoryReadRepository
from app.domain.memory.queries.facade import MemoryQueryFacade
from app.domain.memory.graph.storage import SqlAlchemyGraphStorageProvider
from app.domain.memory.graph.facade import KnowledgeGraphFacade
from app.domain.memory.intelligence.pipeline import ContextPipeline
from app.domain.memory.intelligence.models import ContextScope, ContextCompletenessStatus
from app.domain.memory.intelligence.schemas import ContextRequestOptions, ExportTargetFormat
from app.domain.memory.intelligence.validation import CrossWorkspaceContextError

# ── Fixtures ────────────────────────────────────────────────────────────────

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

# ── 1. MISSING_REQUIRED_CONTEXT & 6. SAFE_EMPTY_CONTEXT ──────────────────────

@pytest.mark.asyncio
async def test_b6_missing_required_context(db_session: AsyncSession):
    ws_id = uuid.uuid4()
    cust_id = uuid.uuid4()  # Does not exist in DB

    pipeline = _make_pipeline(db_session)
    result = await pipeline.execute(
        scope=ContextScope.CUSTOMER,
        entity_id=str(cust_id),
        workspace_id=ws_id,
        options=ContextRequestOptions(format=ExportTargetFormat.STANDARD_API),
    )

    blocks = result.get("blocks", {})
    completeness = result.get("completeness", {})

    # No fabricated memory
    assert "MEMORY" not in blocks or blocks["MEMORY"]["data"] is None or blocks["MEMORY"]["data"] == {}
    # Deterministic empty context
    assert completeness.get("status") in [ContextCompletenessStatus.DEGRADED.value, ContextCompletenessStatus.INCOMPLETE.value]

# ── 2. INVALID_ENTITY_REFERENCE (API Boundary) ──────────────────────────────

def test_b6_invalid_entity_reference_returns_422():
    client = TestClient(fastapi_app)
    ws_id = uuid.uuid4()
    
    # "not-a-uuid" should be rejected by FastAPI Pydantic schema validation for customer_id
    response = client.get(f"/api/v1/memory/context/customer/not-a-uuid?workspace_id={ws_id}")
    assert response.status_code == 422, "Malformed UUID must return HTTP 422"

# ── 3. CONTEXT_RETRIEVAL_FAILURE ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_b6_context_retrieval_failure_degrades(db_session: AsyncSession, monkeypatch):
    ws_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    pipeline = _make_pipeline(db_session)
    
    # Simulate DB exception
    async def mock_get(*args, **kwargs):
        raise ValueError("Database connection dropped")
    
    monkeypatch.setattr(pipeline._query_facade, "get_customer_memory", mock_get)

    result = await pipeline.execute(
        scope=ContextScope.CUSTOMER,
        entity_id=str(cust_id),
        workspace_id=ws_id,
        options=ContextRequestOptions(format=ExportTargetFormat.STANDARD_API),
    )

    completeness = result.get("completeness", {})
    warnings = completeness.get("warnings", [])
    
    # Expect failure to degrade gracefully, not crash
    assert completeness.get("status") in [ContextCompletenessStatus.DEGRADED.value, ContextCompletenessStatus.INCOMPLETE.value]
    assert any("Retrieval failure" in w for w in warnings), "Diagnostic warning should be appended"

# ── 4 & 5. GRAPH_TRAVERSAL_FAILURE / PROJECTION_FAILURE ──────────────────────

@pytest.mark.asyncio
async def test_b6_graph_traversal_and_projection_failure_degrades(db_session: AsyncSession, monkeypatch):
    ws_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    pipeline = _make_pipeline(db_session)
    
    # Simulate DB exception in Graph
    async def mock_traverse(*args, **kwargs):
        raise ValueError("Graph timeout")
    
    async def mock_project(*args, **kwargs):
        raise ValueError("Projection calculation error")
        
    monkeypatch.setattr(pipeline._graph_facade.queries, "traverse_neighbors", mock_traverse)
    monkeypatch.setattr(pipeline._graph_facade.queries, "project_customer_360", mock_project)

    result = await pipeline.execute(
        scope=ContextScope.CUSTOMER,
        entity_id=str(cust_id),
        workspace_id=ws_id,
        options=ContextRequestOptions(max_graph_depth=2, format=ExportTargetFormat.STANDARD_API),
    )

    completeness = result.get("completeness", {})
    warnings = completeness.get("warnings", [])
    
    # Pipeline shouldn't crash; degraded + diagnostics
    assert any("Graph traversal failure" in w for w in warnings) or any("Projection failure" in w for w in warnings)

# ── 7. WORKSPACE_AUTHORIZATION_FAILURE ───────────────────────────────────────

@pytest.mark.asyncio
async def test_b6_workspace_authorization_failure_closes(db_session: AsyncSession):
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()
    cust_id = uuid.uuid4()

    db_session.add(Customer(id=cust_id, workspace_id=ws_b, name="Workspace B Customer", phone="+1000000003"))
    db_session.add(CustomerMemory(
        id=uuid.uuid4(),
        customer_id=cust_id,
        workspace_id=ws_b,
        memory_payload={"secret": "B_DATA"},
        revision_id=str(uuid.uuid4()),
        is_deleted=False,
    ))
    await db_session.commit()

    pipeline = _make_pipeline(db_session)
    
    # We must explicitly bypass the query_facade's repository workspace predicate, 
    # to simulate the case where a compromised repository returns foreign data, 
    # to ensure the Pipeline Step 3 Validator fails closed.
    # We patch the read_repo to return B's data regardless of workspace_id.
    async def malicious_get(*args, **kwargs):
        record = await pipeline._read_repo.get_by_customer_id(customer_id=cust_id, workspace_id=ws_b)
        if record:
            return {"workspace_id": str(record.workspace_id), "customer_id": str(record.customer_id)}
        return None
        
    pipeline._query_facade.get_customer_memory = malicious_get
    
    with pytest.raises(CrossWorkspaceContextError):
        await pipeline.execute(
            scope=ContextScope.CUSTOMER,
            entity_id=str(cust_id),
            workspace_id=ws_a,  # Attempting to fetch as Workspace A
            options=ContextRequestOptions(format=ExportTargetFormat.STANDARD_API),
        )
