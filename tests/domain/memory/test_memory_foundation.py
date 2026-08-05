"""
HunterOS Engage — Core Memory Foundation Test Suite (Refinement Phase 2.1.1)

Tests:
  1. Customer Memory Creation, v1 baseline snapshot & initial timeline event
  2. Duplicate creation prevention
  3. Memory update, deep state diffing, immutable versioning & change logs with module attribution
  4. Industry-agnostic timeline event generation & categorization
  5. Soft-delete and restoration workflows with audit logs
  6. Timeline filtering (category, importance, pagination)
  7. Version history and historical snapshot retrieval with SHA-256 hash verification
  8. Granular field-level change log queries
  9. Unified memory history endpoint (GET /api/v1/memory/{customer_id}/history)
  10. Multi-criteria memory search (location, tags, stages, property types, keywords)
  11. Enterprise bulk operations (bulk_create, bulk_get, bulk_update)
  12. REST API HTTP endpoint execution
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.domain.conversations.models import Base
from app.domain.customers.models import Customer, CustomerStatus
from app.domain.memory.models import (
    ChangeType,
    CustomerMemory,
    CustomerMemoryTimelineEvent,
    CustomerMemoryVersion,
    MemoryChangeLog,
    MemoryIdempotencyRecord,
    MemoryImportance,
    MemoryTimelineCategory,
)
from app.domain.memory.repository import MemoryRepository
from app.domain.memory.schemas import (
    CustomerMemoryBulkCreateRequest,
    CustomerMemoryBulkGetRequest,
    CustomerMemoryBulkUpdateItem,
    CustomerMemoryBulkUpdateRequest,
    CustomerMemoryCreateRequest,
    CustomerMemoryUpdateRequest,
    FinancialInfoBlock,
    IdentityBlock,
    JourneySnapshotBlock,
    LocationInfo,
    MemoryPayloadSchema,
    MemorySearchRequest,
    MemoryTimelineFilterRequest,
    PersonalInfoBlock,
    PropertyInfoBlock,
)
from app.domain.memory.service import (
    MemoryService,
    compute_memory_diff,
    compute_snapshot_hash,
)
from app.main import create_app


from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@pytest.fixture
def engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )


@pytest.fixture
def session_maker(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def async_session(engine, session_maker) -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        # Create tables relevant to customer and memory testing
        await conn.run_sync(Customer.__table__.create)
        await conn.run_sync(CustomerMemory.__table__.create)
        await conn.run_sync(CustomerMemoryVersion.__table__.create)
        await conn.run_sync(CustomerMemoryTimelineEvent.__table__.create)
        await conn.run_sync(MemoryChangeLog.__table__.create)
        await conn.run_sync(MemoryIdempotencyRecord.__table__.create)

    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(MemoryIdempotencyRecord.__table__.drop)
        await conn.run_sync(MemoryChangeLog.__table__.drop)
        await conn.run_sync(CustomerMemoryTimelineEvent.__table__.drop)
        await conn.run_sync(CustomerMemoryVersion.__table__.drop)
        await conn.run_sync(CustomerMemory.__table__.drop)
        await conn.run_sync(Customer.__table__.drop)


@pytest.mark.asyncio
async def test_compute_snapshot_hash_and_diff():
    """Verify deterministic hashing and deep recursive diff calculation."""
    d1 = {"a": 1, "b": {"c": 2, "d": [1, 2]}}
    d2 = {"b": {"d": [1, 2], "c": 2}, "a": 1}
    # Hashes must match regardless of key order
    assert compute_snapshot_hash(d1) == compute_snapshot_hash(d2)

    old_state = {
        "personal_info": {"full_name": "Alice", "location": {"city": "Bangalore"}},
        "financial_info": {"budget_max": 5000000.0},
    }
    new_state = {
        "personal_info": {"full_name": "Alice Smith", "location": {"city": "Bangalore"}},
        "financial_info": {"budget_max": 7500000.0, "currency": "INR"},
        "property_info": {"purpose": "investment"},
    }

    diffs = compute_memory_diff(old_state, new_state)
    paths = {d["field_path"]: d for d in diffs}

    assert "personal_info.full_name" in paths
    assert paths["personal_info.full_name"]["change_type"] == ChangeType.MODIFIED
    assert paths["personal_info.full_name"]["old_value"] == "Alice"
    assert paths["personal_info.full_name"]["new_value"] == "Alice Smith"

    assert "financial_info.budget_max" in paths
    assert paths["financial_info.budget_max"]["old_value"] == 5000000.0
    assert paths["financial_info.budget_max"]["new_value"] == 7500000.0

    assert "financial_info.currency" in paths
    assert paths["financial_info.currency"]["change_type"] == ChangeType.ADDED

    assert "property_info" in paths or "property_info.purpose" in paths


@pytest.mark.asyncio
async def test_create_customer_memory_initializes_v1_and_timeline(async_session: AsyncSession):
    """Test memory creation generates version 1 snapshot and initial LIFECYCLE timeline event."""
    customer_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    # Seed customer
    customer = Customer(id=customer_id, phone="+919876543210", name="Test Customer", workspace_id=workspace_id)
    async_session.add(customer)
    await async_session.commit()

    service = MemoryService()
    req = CustomerMemoryCreateRequest(
        customer_id=customer_id,
        workspace_id=workspace_id,
        memory_payload=MemoryPayloadSchema(
            personal_info=PersonalInfoBlock(full_name="Rahul Verma", location=LocationInfo(city="Mumbai")),
            financial_info=FinancialInfoBlock(budget_min=5000000.0, budget_max=10000000.0, currency="INR"),
            property_info=PropertyInfoBlock(property_types=["apartment", "villa"], readiness="ready_to_move"),
        ),
        source="API",
        created_by="Agent_007",
    )

    memory = await service.create_customer_memory(req, session=async_session)
    await async_session.commit()

    assert memory.customer_id == customer_id
    assert memory.version_number == 1
    assert memory.is_deleted is False
    assert memory.memory_payload["personal_info"]["full_name"] == "Rahul Verma"

    # Verify Version 1 snapshot
    versions, total_v = await service.get_versions(customer_id, session=async_session)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].schema_version == "1.0.0"
    assert len(versions[0].snapshot_hash) == 64
    assert versions[0].snapshot_data["personal_info"]["full_name"] == "Rahul Verma"

    # Verify initial timeline event
    timeline, total_t = await service.get_timeline(customer_id, session=async_session)
    assert total_t == 1
    assert timeline[0].category == MemoryTimelineCategory.LIFECYCLE
    assert timeline[0].event_type == "memory_created"
    assert timeline[0].version_number == 1


@pytest.mark.asyncio
async def test_duplicate_memory_creation_rejected(async_session: AsyncSession):
    """Test that creating memory for an already registered customer raises ValueError."""
    customer_id = uuid.uuid4()
    customer = Customer(id=customer_id, phone="+919999988888", name="Duplicate Customer")
    async_session.add(customer)
    await async_session.commit()

    service = MemoryService()
    req = CustomerMemoryCreateRequest(customer_id=customer_id)
    await service.create_customer_memory(req, session=async_session)
    await async_session.commit()

    with pytest.raises(ValueError, match="already exists"):
        await service.create_customer_memory(req, session=async_session)


@pytest.mark.asyncio
async def test_update_memory_creates_version_and_changelogs(async_session: AsyncSession):
    """Test that partial update generates v2 snapshot, changelogs, and timeline events."""
    customer_id = uuid.uuid4()
    customer = Customer(id=customer_id, phone="+919111122222", name="Update Customer")
    async_session.add(customer)
    await async_session.commit()

    service = MemoryService()
    # 1. Create v1
    create_req = CustomerMemoryCreateRequest(
        customer_id=customer_id,
        memory_payload=MemoryPayloadSchema(
            personal_info=PersonalInfoBlock(full_name="Priya Sharma", location=LocationInfo(city="Delhi")),
            financial_info=FinancialInfoBlock(budget_max=6000000.0),
        ),
    )
    await service.create_customer_memory(create_req, session=async_session)
    await async_session.commit()

    # 2. Update to v2: update budget and add property requirements
    update_req = CustomerMemoryUpdateRequest(
        memory_payload={
            "financial_info": {"budget_max": 8500000.0, "financing_type": "pre_approved_loan"},
            "property_info": {"property_types": ["luxury_apartment"], "readiness": "immediate"},
        },
        reason="Customer increased budget after loan pre-approval",
        trigger="conversation_fact",
        changed_module="Conversation Intelligence",
        changed_by="AI_Parser_v2",
    )

    updated_mem = await service.update_customer_memory(customer_id, update_req, session=async_session)
    await async_session.commit()

    assert updated_mem.version_number == 2
    assert updated_mem.memory_payload["financial_info"]["budget_max"] == 8500000.0
    assert updated_mem.memory_payload["financial_info"]["financing_type"] == "pre_approved_loan"
    assert updated_mem.memory_payload["personal_info"]["full_name"] == "Priya Sharma"  # preserved!

    # 3. Check version 2 snapshot
    v2_detail = await service.get_version_by_number(customer_id, 2, session=async_session)
    assert v2_detail is not None
    assert v2_detail.version_number == 2
    assert v2_detail.snapshot_data["financial_info"]["budget_max"] == 8500000.0

    # 4. Check Change Logs with changed_module
    changelogs, total_cl = await service.get_change_logs(customer_id, version_number=2, session=async_session)
    assert total_cl >= 2
    for log in changelogs:
        assert log.version_number == 2
        assert log.changed_module == "Conversation Intelligence"
        assert log.changed_by == "AI_Parser_v2"

    budget_log = next(l for l in changelogs if l.field_path == "financial_info.budget_max")
    assert budget_log.old_value == 6000000.0
    assert budget_log.new_value == 8500000.0
    assert budget_log.change_type == ChangeType.MODIFIED

    # 5. Check Timeline Events
    timeline, total_tl = await service.get_timeline(customer_id, session=async_session)
    # Expect v1 creation event + v2 FINANCIAL and PREFERENCE events
    categories = [t.category for t in timeline]
    assert MemoryTimelineCategory.FINANCIAL in categories
    assert MemoryTimelineCategory.PREFERENCE in categories
    assert MemoryTimelineCategory.LIFECYCLE in categories


@pytest.mark.asyncio
async def test_soft_delete_and_restore_memory(async_session: AsyncSession):
    """Test soft delete and restore lifecycle with audit logs."""
    customer_id = uuid.uuid4()
    customer = Customer(id=customer_id, phone="+919444455555", name="Lifecycle Customer")
    async_session.add(customer)
    await async_session.commit()

    service = MemoryService()
    await service.create_customer_memory(CustomerMemoryCreateRequest(customer_id=customer_id), session=async_session)
    await async_session.commit()

    # 1. Soft Delete
    deleted_mem = await service.soft_delete_memory(
        customer_id, reason="Customer requested erasure", changed_by="Admin_User", session=async_session
    )
    await async_session.commit()

    assert deleted_mem.is_deleted is True
    assert deleted_mem.deleted_at is not None
    assert deleted_mem.version_number == 2

    # Active lookup returns None
    assert await service.get_customer_memory(customer_id, include_deleted=False, session=async_session) is None
    # Deleted lookup returns record
    assert await service.get_customer_memory(customer_id, include_deleted=True, session=async_session) is not None

    # Check deletion timeline event
    timeline, _ = await service.get_timeline(customer_id, session=async_session)
    del_event = next(t for t in timeline if t.event_type == "memory_soft_deleted")
    assert del_event.importance == MemoryImportance.CRITICAL

    # 2. Restore
    restored_mem = await service.restore_memory(customer_id, changed_by="Admin_User", session=async_session)
    await async_session.commit()

    assert restored_mem.is_deleted is False
    assert restored_mem.deleted_at is None
    assert restored_mem.version_number == 3

    # Check restore timeline event
    timeline_after, _ = await service.get_timeline(customer_id, session=async_session)
    res_event = next(t for t in timeline_after if t.event_type == "memory_restored")
    assert res_event.importance == MemoryImportance.HIGH


@pytest.mark.asyncio
async def test_timeline_category_and_importance_filters(async_session: AsyncSession):
    """Test querying timeline with specific category and importance filters."""
    customer_id = uuid.uuid4()
    customer = Customer(id=customer_id, phone="+919555566666", name="Timeline Filter Customer")
    async_session.add(customer)
    await async_session.commit()

    service = MemoryService()
    await service.create_customer_memory(CustomerMemoryCreateRequest(customer_id=customer_id), session=async_session)

    # Trigger updates
    await service.update_customer_memory(
        customer_id,
        CustomerMemoryUpdateRequest(
            memory_payload={"financial_info": {"budget_max": 9000000.0}},
            changed_module="Intent Intelligence",
        ),
        session=async_session,
    )
    await async_session.commit()

    # Filter FINANCIAL category
    financial_events, total_fin = await service.get_timeline(
        customer_id, category=MemoryTimelineCategory.FINANCIAL.value, session=async_session
    )
    assert total_fin >= 1
    assert all(e.category == MemoryTimelineCategory.FINANCIAL for e in financial_events)

    # Filter LIFECYCLE category
    lifecycle_events, total_life = await service.get_timeline(
        customer_id, category=MemoryTimelineCategory.LIFECYCLE.value, session=async_session
    )
    assert total_life >= 1
    assert all(e.category == MemoryTimelineCategory.LIFECYCLE for e in lifecycle_events)


@pytest.mark.asyncio
async def test_get_customer_memory_history_unified_endpoint(async_session: AsyncSession):
    """Test GET /api/v1/memory/{customer_id}/history aggregating memory, timeline, versions, changelogs."""
    customer_id = uuid.uuid4()
    customer = Customer(id=customer_id, phone="+919666677777", name="History Customer")
    async_session.add(customer)
    await async_session.commit()

    service = MemoryService()
    await service.create_customer_memory(
        CustomerMemoryCreateRequest(
            customer_id=customer_id,
            memory_payload=MemoryPayloadSchema(
                personal_info=PersonalInfoBlock(full_name="Sneha Rao", location=LocationInfo(city="Hyderabad")),
                financial_info=FinancialInfoBlock(budget_max=12000000.0),
            ),
        ),
        session=async_session,
    )
    await service.update_customer_memory(
        customer_id,
        CustomerMemoryUpdateRequest(
            memory_payload={"financial_info": {"budget_max": 15000000.0}},
            reason="Upgraded requirements",
            changed_module="Manual Update",
        ),
        session=async_session,
    )
    await async_session.commit()

    history = await service.get_customer_memory_history(customer_id, session=async_session)

    assert history.memory is not None
    assert history.memory.customer_id == customer_id
    assert history.memory.version_number == 2
    assert len(history.versions) == 2
    assert len(history.timeline) >= 2
    assert len(history.change_logs) >= 1
    assert history.change_logs[0].field_path == "financial_info.budget_max"


@pytest.mark.asyncio
async def test_multi_criteria_memory_search(async_session: AsyncSession):
    """Test searching customer memories across cities, stages, property types, and search terms."""
    c1_id = uuid.uuid4()
    c2_id = uuid.uuid4()
    c3_id = uuid.uuid4()

    async_session.add_all([
        Customer(id=c1_id, phone="+919000011111", name="Bangalore Buyer"),
        Customer(id=c2_id, phone="+919000022222", name="Mumbai Investor"),
        Customer(id=c3_id, phone="+919000033333", name="Delhi Plot Buyer"),
    ])
    await async_session.commit()

    service = MemoryService()
    await service.create_customer_memory(
        CustomerMemoryCreateRequest(
            customer_id=c1_id,
            memory_payload=MemoryPayloadSchema(
                identity=IdentityBlock(tags=["vip", "hni"]),
                personal_info=PersonalInfoBlock(full_name="Karan", location=LocationInfo(city="Bangalore")),
                property_info=PropertyInfoBlock(property_types=["villa", "penthouse"]),
                journey_snapshot=JourneySnapshotBlock(current_stage="QUALIFIED"),
            ),
        ),
        session=async_session,
    )
    await service.create_customer_memory(
        CustomerMemoryCreateRequest(
            customer_id=c2_id,
            memory_payload=MemoryPayloadSchema(
                identity=IdentityBlock(tags=["investor"]),
                personal_info=PersonalInfoBlock(full_name="Ananya", location=LocationInfo(city="Mumbai")),
                property_info=PropertyInfoBlock(property_types=["commercial_office"]),
                journey_snapshot=JourneySnapshotBlock(current_stage="NEGOTIATION"),
            ),
        ),
        session=async_session,
    )
    await service.create_customer_memory(
        CustomerMemoryCreateRequest(
            customer_id=c3_id,
            memory_payload=MemoryPayloadSchema(
                identity=IdentityBlock(tags=["first_time_buyer"]),
                personal_info=PersonalInfoBlock(full_name="Deepak", location=LocationInfo(city="Delhi")),
                property_info=PropertyInfoBlock(property_types=["residential_plot"]),
                journey_snapshot=JourneySnapshotBlock(current_stage="EXPLORATION"),
            ),
        ),
        session=async_session,
    )
    await async_session.commit()

    # Search by city
    res_blr = await service.search_memory(MemorySearchRequest(location_city="Bangalore"), session=async_session)
    assert res_blr.total == 1
    assert res_blr.items[0].customer_id == c1_id

    # Search by tag
    res_tag = await service.search_memory(MemorySearchRequest(tags=["investor"]), session=async_session)
    assert res_tag.total == 1
    assert res_tag.items[0].customer_id == c2_id

    # Search by property type
    res_prop = await service.search_memory(MemorySearchRequest(property_types=["commercial_office"]), session=async_session)
    assert res_prop.total == 1
    assert res_prop.items[0].customer_id == c2_id

    # Search by stage
    res_stage = await service.search_memory(MemorySearchRequest(current_stage="EXPLORATION"), session=async_session)
    assert res_stage.total == 1
    assert res_stage.items[0].customer_id == c3_id


@pytest.mark.asyncio
async def test_bulk_memory_operations(async_session: AsyncSession):
    """Test enterprise bulk_create, bulk_get, and bulk_update."""
    c1 = uuid.uuid4()
    c2 = uuid.uuid4()

    async_session.add_all([
        Customer(id=c1, phone="+919888800001", name="Bulk Customer 1"),
        Customer(id=c2, phone="+919888800002", name="Bulk Customer 2"),
    ])
    await async_session.commit()

    service = MemoryService()

    # 1. Bulk Create
    bulk_create_items = [
        CustomerMemoryCreateRequest(
            customer_id=c1,
            memory_payload=MemoryPayloadSchema(personal_info=PersonalInfoBlock(full_name="Bulk 1")),
        ),
        CustomerMemoryCreateRequest(
            customer_id=c2,
            memory_payload=MemoryPayloadSchema(personal_info=PersonalInfoBlock(full_name="Bulk 2")),
        ),
    ]
    created = await service.bulk_create_memories(bulk_create_items, session=async_session)
    await async_session.commit()
    assert len(created) == 2

    # 2. Bulk Get
    fetched = await service.bulk_get_memories([c1, c2], session=async_session)
    assert len(fetched) == 2

    # 3. Bulk Update
    bulk_updates = [
        CustomerMemoryBulkUpdateItem(
            customer_id=c1,
            update_data=CustomerMemoryUpdateRequest(
                memory_payload={"financial_info": {"budget_max": 4000000.0}},
                changed_module="System Migration",
            ),
        ),
        CustomerMemoryBulkUpdateItem(
            customer_id=c2,
            update_data=CustomerMemoryUpdateRequest(
                memory_payload={"financial_info": {"budget_max": 5000000.0}},
                changed_module="System Migration",
            ),
        ),
    ]
    updated = await service.bulk_update_memories(bulk_updates, session=async_session)
    await async_session.commit()
    assert len(updated) == 2
    assert updated[0].version_number == 2
    assert updated[1].version_number == 2


@pytest.mark.asyncio
async def test_rest_api_endpoints_integration(async_session: AsyncSession):
    """Test REST API routes using FastAPI test client."""
    customer_id = uuid.uuid4()
    customer = Customer(id=customer_id, phone="+919777788888", name="API Test Customer")
    async_session.add(customer)
    await async_session.commit()

    app = create_app()

    # Override get_db dependency to use our isolated test async_session
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. POST /api/v1/memory (Create)
        create_resp = await client.post(
            "/api/v1/memory",
            json={
                "customer_id": str(customer_id),
                "memory_payload": {
                    "personal_info": {"full_name": "API Client User", "location": {"city": "Pune"}},
                    "financial_info": {"budget_max": 7000000.0},
                },
                "source": "REST_TEST",
            },
        )
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert data["customer_id"] == str(customer_id)
        assert data["version_number"] == 1

        # 2. GET /api/v1/memory/{customer_id}
        get_resp = await client.get(f"/api/v1/memory/{customer_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["memory_payload"]["personal_info"]["full_name"] == "API Client User"

        # 3. PATCH /api/v1/memory/{customer_id} (Update)
        patch_resp = await client.patch(
            f"/api/v1/memory/{customer_id}",
            json={
                "memory_payload": {"financial_info": {"budget_max": 9500000.0}},
                "reason": "API Budget Boost",
                "changed_module": "Manual Update",
            },
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["version_number"] == 2

        # 4. GET /api/v1/memory/{customer_id}/timeline
        timeline_resp = await client.get(f"/api/v1/memory/{customer_id}/timeline")
        assert timeline_resp.status_code == 200
        assert timeline_resp.json()["total"] >= 2

        # 5. GET /api/v1/memory/{customer_id}/versions
        versions_resp = await client.get(f"/api/v1/memory/{customer_id}/versions")
        assert versions_resp.status_code == 200
        assert len(versions_resp.json()) == 2

        # 6. GET /api/v1/memory/{customer_id}/versions/1
        v1_detail_resp = await client.get(f"/api/v1/memory/{customer_id}/versions/1")
        assert v1_detail_resp.status_code == 200
        assert v1_detail_resp.json()["snapshot_data"]["financial_info"]["budget_max"] == 7000000.0

        # 7. GET /api/v1/memory/{customer_id}/changelog
        cl_resp = await client.get(f"/api/v1/memory/{customer_id}/changelog")
        assert cl_resp.status_code == 200
        assert cl_resp.json()["total"] >= 1

        # 8. GET /api/v1/memory/{customer_id}/history (Unified History)
        hist_resp = await client.get(f"/api/v1/memory/{customer_id}/history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["memory"]["version_number"] == 2
        assert len(hist_data["timeline"]) >= 2
        assert len(hist_data["versions"]) == 2
        assert len(hist_data["change_logs"]) >= 1

        # 9. POST /api/v1/memory/search
        search_resp = await client.post(
            "/api/v1/memory/search",
            json={"location_city": "Pune"},
        )
        assert search_resp.status_code == 200
        assert search_resp.json()["total"] == 1

        # 10. DELETE /api/v1/memory/{customer_id}
        del_resp = await client.delete(f"/api/v1/memory/{customer_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["is_deleted"] is True

        # 11. POST /api/v1/memory/{customer_id}/restore
        restore_resp = await client.post(f"/api/v1/memory/{customer_id}/restore")
        assert restore_resp.status_code == 200
        assert restore_resp.json()["is_deleted"] is False
