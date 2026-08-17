import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import ASGITransport, AsyncClient

import app.domain.conversations.models  # Fix circular import
from app.domain.customers.models import Customer, Base as CustBase
from app.domain.memory.models import Base as MemBase, CustomerMemory, CustomerMemoryTimelineEvent, MemoryTimelineCategory, MemoryEventType, MemoryImportance
from app.domain.memory.service import MemoryService
from app.domain.memory.schemas import (
    CustomerMemoryCreateRequest,
    CustomerMemoryUpdateRequest,
)
from app.domain.memory.validators.base import MemoryValidationError

from app.main import app
from app.api.v1.auth_deps import get_current_user
from app.domain.security.models import User, UserRole
from app.integrations.postgres.database import get_db

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

    async with session_maker() as session:
        yield session

@pytest_asyncio.fixture
async def setup_workspaces(db_session: AsyncSession):
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()
    
    # Workspace A data
    cust_a = Customer(id=uuid.uuid4(), workspace_id=ws_a, phone="+1000000000A", name="Cust A", buying_stage="Purchase Ready")
    db_session.add(cust_a)
    
    # Workspace B data
    cust_b = Customer(id=uuid.uuid4(), workspace_id=ws_b, phone="+1000000000B", name="Cust B", buying_stage="Research")
    db_session.add(cust_b)
    
    await db_session.commit()
    
    # Seed memories directly
    service = MemoryService()
    mem_a = await service.create_customer_memory(
        CustomerMemoryCreateRequest(customer_id=cust_a.id, workspace_id=ws_a, memory_payload={"key": "PayloadSearchTargetA"}), db_session
    )
    await service.create_customer_memory(
        CustomerMemoryCreateRequest(customer_id=cust_b.id, workspace_id=ws_b, memory_payload={"key": "PayloadSearchTargetB"}), db_session
    )
    
    # Seed a timeline event
    evt = CustomerMemoryTimelineEvent(
        id=uuid.uuid4(),
        customer_id=cust_a.id,
        memory_id=mem_a.id,
        category=MemoryTimelineCategory.MANUAL,
        event_type=MemoryEventType.memory_created,
        title="Created Memory",
        importance=MemoryImportance.MEDIUM,
        description="Created",
    )
    db_session.add(evt)
    await db_session.commit()
    
    return ws_a, ws_b, cust_a.id, cust_b.id

@pytest.fixture
def override_deps(db_session):
    def _override(user_ws: uuid.UUID = None):
        app.dependency_overrides[get_db] = lambda: db_session
        if user_ws:
            app.dependency_overrides[get_current_user] = lambda: User(id=uuid.uuid4(), role=UserRole.founder, workspace_id=user_ws)
        else:
            if get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]
    yield _override
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_memory_api_unauthenticated(setup_workspaces, override_deps):
    ws_a, ws_b, cust_a_id, cust_b_id = setup_workspaces
    override_deps(None) # No user override, should fail natively
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/api/v1/memory/{cust_a_id}")
        assert resp.status_code == 403 # FastAPI HTTPBearer returns 403 when not provided

@pytest.mark.asyncio
async def test_memory_api_isolation_reads(setup_workspaces, override_deps):
    ws_a, ws_b, cust_a_id, cust_b_id = setup_workspaces
    override_deps(ws_b) # Authenticated as B
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # B tries to read A
        resp = await client.get(f"/api/v1/memory/{cust_a_id}")
        assert resp.status_code == 404
        
        # B tries to read B
        resp = await client.get(f"/api/v1/memory/{cust_b_id}")
        assert resp.status_code == 200
        
        # Timeline
        resp = await client.get(f"/api/v1/memory/{cust_a_id}/timeline")
        assert len(resp.json()["items"]) == 0 # Cannot see A's timeline

@pytest.mark.asyncio
async def test_memory_api_isolation_writes(setup_workspaces, override_deps):
    ws_a, ws_b, cust_a_id, cust_b_id = setup_workspaces
    override_deps(ws_b) # Authenticated as B
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Get ETag for A using A's token first to try writing with B
        override_deps(ws_a)
        r = await client.get(f"/api/v1/memory/{cust_a_id}")
        etag = r.headers.get("etag")
        
        # Switch back to B
        override_deps(ws_b)
        resp = await client.patch(
            f"/api/v1/memory/{cust_a_id}",
            json={"memory_payload": {"hacked": True}, "workspace_id": str(ws_b)}, # Trying to trick it with client ws_id
            headers={"If-Match": etag}
        )
        assert resp.status_code in [403, 404, 422] # Either domain blocks it, or validation blocks it, or 404

@pytest.mark.asyncio
async def test_memory_api_isolation_search(setup_workspaces, override_deps):
    ws_a, ws_b, cust_a_id, cust_b_id = setup_workspaces
    override_deps(ws_b) # Authenticated as B
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Try to search for A's payload ("key": "A")
        # Supplying workspace_id=ws_a maliciously
        resp = await client.post(
            "/api/v1/memory/search",
            json={"workspace_id": str(ws_a), "search_term": "PayloadSearchTargetA"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 0 # Should be empty because it forces current_user.workspace_id = ws_b
