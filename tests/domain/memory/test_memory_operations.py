"""
HunterOS Engage — Memory Intelligence: Memory Operations & Lifecycle Management Test Suite (Phase 2.1.2)

Comprehensive test coverage for:
  1. Command Handlers (Create, Update, Replace, Delete, Restore, ChangeStatus)
  2. MemoryCommandBus Dispatching & Idempotency deduplication
  3. MemoryUnitOfWork Transactional Atomicity (Rollback on failure, commit + event dispatch)
  4. Optimistic Concurrency Control (revision_id / ETag verification & HTTP 412 Precondition Failed)
  5. 5-Stage Validation Pipeline (Schema, Domain, Business Rules, Persistence)
  6. Lifecycle Status Machine (ACTIVE, LOCKED, ARCHIVED, DELETED) & Guard Invariants (HTTP 423 Locked)
  7. Domain Event Publishing (MemoryCreated, MemoryUpdated, MemoryDeleted, MemoryRestored, MemoryStatusChanged)
  8. REST API Endpoints (POST, PATCH, PUT, DELETE, POST /restore, POST /status)
"""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.domain.customers.models import Customer
from app.domain.memory import (
    ArchiveMemoryCommand,
    ChangeStatusCommand,
    CreateMemoryCommand,
    CustomerMemory,
    CustomerMemoryTimelineEvent,
    CustomerMemoryVersion,
    DeleteMemoryCommand,
    LifecycleStatus,
    LockMemoryCommand,
    MemoryChangeLog,
    MemoryCommandBus,
    MemoryDomainError,
    MemoryEventPublisher,
    MemoryIdempotencyRecord,
    MemoryImportance,
    MemoryService,
    MemoryTimelineCategory,
    MemoryUnitOfWork,
    MemoryValidationError,
    ReplaceMemoryCommand,
    RestoreMemoryCommand,
    UnlockMemoryCommand,
    UpdateMemoryCommand,
)
from app.domain.memory.commands.change_status import ChangeStatusHandler
from app.domain.memory.commands.create_memory import CreateMemoryHandler
from app.domain.memory.commands.delete_memory import DeleteMemoryHandler
from app.domain.memory.commands.replace_memory import ReplaceMemoryHandler
from app.domain.memory.commands.restore_memory import RestoreMemoryHandler
from app.domain.memory.commands.update_memory import UpdateMemoryHandler
from app.domain.memory.events.models import (
    MemoryCreatedDomainEvent,
    MemoryDeletedDomainEvent,
    MemoryRestoredDomainEvent,
    MemoryStatusChangedDomainEvent,
    MemoryUpdatedDomainEvent,
)
from app.domain.memory.models import MemoryConcurrencyConflictError
from app.domain.memory.schemas import (
    CustomerMemoryCreateRequest,
    CustomerMemoryReplaceRequest,
    CustomerMemoryStatusChangeRequest,
    CustomerMemoryUpdateRequest,
    FinancialInfoBlock,
    IdentityBlock,
    LocationInfo,
    MemoryPayloadSchema,
    PersonalInfoBlock,
    PropertyInfoBlock,
)
from app.domain.memory.transactions.idempotency import IdempotencyManager
from app.domain.memory.validators.base import ValidationContext
from app.domain.memory.validators.pipeline import MemoryValidationPipeline
from app.main import create_app


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


# ── 1. Create Memory Command & Handler ───────────────────────────────────────

@pytest.mark.asyncio
async def test_create_memory_command_handler_success(async_session: AsyncSession):
    """Test CreateMemoryHandler executes validation, creates aggregate root, snapshot v1 and events."""
    customer_id = uuid4()
    customer = Customer(id=customer_id, phone="+919876543210", name="Rohan Varma")
    async_session.add(customer)
    await async_session.commit()

    publisher = MemoryEventPublisher()
    uow = MemoryUnitOfWork(event_publisher=publisher)
    handler = CreateMemoryHandler()

    command = CreateMemoryCommand(
        customer_id=customer_id,
        memory_payload={"personal_info": {"full_name": "Rohan Varma", "city": "Bangalore"}},
        actor="lead_orchestrator",
        source="CRM_SYNC",
    )

    async with uow.begin(async_session):
        memory = await handler.handle(async_session, command, uow=uow)

    assert memory is not None
    assert memory.customer_id == customer_id
    assert memory.version_number == 1
    assert memory.lifecycle_status == LifecycleStatus.ACTIVE
    assert memory.revision_id is not None
    assert memory.is_deleted is False

    # Verify domain event published
    published = publisher.get_published_events()
    assert len(published) == 1
    assert isinstance(published[0], MemoryCreatedDomainEvent)
    assert published[0].aggregate_id == memory.id
    assert published[0].version == 1


# ── 2. Update Memory Command & Partial Patch ────────────────────────────────

@pytest.mark.asyncio
async def test_update_memory_command_handler_success(async_session: AsyncSession):
    """Test UpdateMemoryHandler performs deep delta merge, creates v2 snapshot, and emits update event."""
    customer_id = uuid4()
    customer = Customer(id=customer_id, phone="+919876543211", name="Anita Desai")
    async_session.add(customer)
    await async_session.commit()

    publisher = MemoryEventPublisher()
    uow = MemoryUnitOfWork(event_publisher=publisher)
    create_handler = CreateMemoryHandler()
    update_handler = UpdateMemoryHandler()

    # Step 1: Create v1
    create_cmd = CreateMemoryCommand(
        customer_id=customer_id,
        memory_payload={
            "personal_info": {"full_name": "Anita Desai", "location": {"city": "Mumbai"}},
            "financial_info": {"budget_max": 5000000.0},
        },
    )
    async with uow.begin(async_session):
        mem_v1 = await create_handler.handle(async_session, create_cmd, uow=uow)

    v1_revision = mem_v1.revision_id

    # Step 2: Partial Update (PATCH)
    update_cmd = UpdateMemoryCommand(
        customer_id=customer_id,
        memory_payload={
            "financial_info": {"budget_max": 7500000.0, "financing_type": "cash"},
        },
        expected_revision_id=v1_revision,
        reason="Budget expanded by client",
        changed_module="Financial Qualification",
        actor="agent_smith",
    )

    async with uow.begin(async_session):
        mem_v2 = await update_handler.handle(async_session, update_cmd, uow=uow)

    assert mem_v2.version_number == 2
    assert mem_v2.revision_id != v1_revision
    # Deep merge preserved original personal_info
    assert mem_v2.memory_payload["personal_info"]["full_name"] == "Anita Desai"
    assert mem_v2.memory_payload["personal_info"]["location"]["city"] == "Mumbai"
    assert mem_v2.memory_payload["financial_info"]["budget_max"] == 7500000.0
    assert mem_v2.memory_payload["financial_info"]["financing_type"] == "cash"

    # Verify update event published
    published = publisher.get_published_events()
    update_events = [e for e in published if isinstance(e, MemoryUpdatedDomainEvent)]
    assert len(update_events) == 1
    assert update_events[0].old_version == 1
    assert update_events[0].new_version == 2


# ── 3. Replace Memory Command (PUT Full State) ──────────────────────────────

@pytest.mark.asyncio
async def test_replace_memory_command_handler_success(async_session: AsyncSession):
    """Test ReplaceMemoryHandler completely overwrites payload while maintaining schema invariants."""
    customer_id = uuid4()
    customer = Customer(id=customer_id, phone="+919876543212", name="Vikram Roy")
    async_session.add(customer)
    await async_session.commit()

    publisher = MemoryEventPublisher()
    uow = MemoryUnitOfWork(event_publisher=publisher)
    create_handler = CreateMemoryHandler()
    replace_handler = ReplaceMemoryHandler()

    # Step 1: Create v1
    create_cmd = CreateMemoryCommand(
        customer_id=customer_id,
        memory_payload={"personal_info": {"full_name": "Vikram Roy"}, "financial_info": {"budget_max": 2000000.0}},
    )
    async with uow.begin(async_session):
        mem_v1 = await create_handler.handle(async_session, create_cmd, uow=uow)

    v1_revision = mem_v1.revision_id

    # Step 2: Full Replacement (PUT)
    replace_cmd = ReplaceMemoryCommand(
        customer_id=customer_id,
        memory_payload={"personal_info": {"full_name": "Vikram Roy Updated"}, "identity": {"tags": ["enterprise"]}},
        expected_revision_id=v1_revision,
        reason="Full CRM Resync",
        actor="crm_sync_worker",
    )

    async with uow.begin(async_session):
        mem_v2 = await replace_handler.handle(async_session, replace_cmd, uow=uow)

    assert mem_v2.version_number == 2
    assert "financial_info" not in mem_v2.memory_payload  # Replaced, not merged!
    assert mem_v2.memory_payload["personal_info"]["full_name"] == "Vikram Roy Updated"
    assert mem_v2.memory_payload["identity"]["tags"] == ["enterprise"]


# ── 4. Optimistic Concurrency Control (OCC) Conflicts ───────────────────────

@pytest.mark.asyncio
async def test_optimistic_concurrency_control_conflict_handling(async_session: AsyncSession):
    """Test that outdated revision_id or version raises MemoryConcurrencyConflictError."""
    customer_id = uuid4()
    customer = Customer(id=customer_id, phone="+919876543213", name="OCC Test Customer")
    async_session.add(customer)
    await async_session.commit()

    uow = MemoryUnitOfWork()
    create_handler = CreateMemoryHandler()
    update_handler = UpdateMemoryHandler()

    # Create v1
    create_cmd = CreateMemoryCommand(customer_id=customer_id, memory_payload={"personal_info": {"full_name": "OCC"}})
    async with uow.begin(async_session):
        await create_handler.handle(async_session, create_cmd, uow=uow)

    # Attempt update with stale/invalid revision_id
    stale_cmd = UpdateMemoryCommand(
        customer_id=customer_id,
        memory_payload={"personal_info": {"full_name": "OCC Stale"}},
        expected_revision_id="stale-revision-etag-999",
    )

    with pytest.raises(MemoryConcurrencyConflictError) as exc_info:
        async with uow.begin(async_session):
            await update_handler.handle(async_session, stale_cmd, uow=uow)

    assert "Concurrency conflict" in str(exc_info.value)
    assert exc_info.value.expected_revision == "stale-revision-etag-999"


# ── 5. Lifecycle Status Transitions & Guard Invariants ──────────────────────

@pytest.mark.asyncio
async def test_lifecycle_status_machine_and_invariants(async_session: AsyncSession):
    """Test transitions: ACTIVE -> LOCKED -> ACTIVE, ACTIVE -> ARCHIVED, and mutations on LOCKED memory rejected."""
    customer_id = uuid4()
    customer = Customer(id=customer_id, phone="+919876543214", name="Lifecycle State Customer")
    async_session.add(customer)
    await async_session.commit()

    publisher = MemoryEventPublisher()
    uow = MemoryUnitOfWork(event_publisher=publisher)
    create_handler = CreateMemoryHandler()
    status_handler = ChangeStatusHandler()
    update_handler = UpdateMemoryHandler()

    # 1. Create Active Memory
    create_cmd = CreateMemoryCommand(customer_id=customer_id, memory_payload={"personal_info": {"full_name": "Active"}})
    async with uow.begin(async_session):
        mem = await create_handler.handle(async_session, create_cmd, uow=uow)

    assert mem.lifecycle_status == LifecycleStatus.ACTIVE

    # 2. Lock Memory
    lock_cmd = ChangeStatusCommand(customer_id=customer_id, target_status=LifecycleStatus.LOCKED, reason="Legal hold")
    async with uow.begin(async_session):
        mem_locked = await status_handler.handle(async_session, lock_cmd, uow=uow)

    assert mem_locked.lifecycle_status == LifecycleStatus.LOCKED

    # 3. Attempt mutation on LOCKED memory -> Must fail
    update_cmd = UpdateMemoryCommand(
        customer_id=customer_id,
        memory_payload={"personal_info": {"full_name": "Illegal Update"}},
    )
    with pytest.raises(MemoryDomainError, match="(?i)locked"):
        async with uow.begin(async_session):
            await update_handler.handle(async_session, update_cmd, uow=uow)

    # 4. Unlock Memory -> Back to ACTIVE
    unlock_cmd = ChangeStatusCommand(customer_id=customer_id, target_status=LifecycleStatus.ACTIVE, reason="Legal hold lifted")
    async with uow.begin(async_session):
        mem_unlocked = await status_handler.handle(async_session, unlock_cmd, uow=uow)

    assert mem_unlocked.lifecycle_status == LifecycleStatus.ACTIVE

    # 5. Archive Memory -> ARCHIVED
    archive_cmd = ChangeStatusCommand(customer_id=customer_id, target_status=LifecycleStatus.ARCHIVED, reason="Customer inactive 2 years")
    async with uow.begin(async_session):
        mem_archived = await status_handler.handle(async_session, archive_cmd, uow=uow)

    assert mem_archived.lifecycle_status == LifecycleStatus.ARCHIVED

    # Verify status changed domain events
    published = publisher.get_published_events()
    status_events = [e for e in published if isinstance(e, MemoryStatusChangedDomainEvent)]
    assert len(status_events) == 3


# ── 6. Soft Delete & Restore Handlers ────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_and_restore_handlers(async_session: AsyncSession):
    """Test DeleteMemoryHandler soft deletes and RestoreMemoryHandler restores active state."""
    customer_id = uuid4()
    customer = Customer(id=customer_id, phone="+919876543215", name="Delete Restore Customer")
    async_session.add(customer)
    await async_session.commit()

    publisher = MemoryEventPublisher()
    uow = MemoryUnitOfWork(event_publisher=publisher)
    create_handler = CreateMemoryHandler()
    delete_handler = DeleteMemoryHandler()
    restore_handler = RestoreMemoryHandler()

    # 1. Create
    async with uow.begin(async_session):
        await create_handler.handle(
            async_session, CreateMemoryCommand(customer_id=customer_id, memory_payload={"personal_info": {"full_name": "Test"}}), uow=uow
        )

    # 2. Soft Delete
    del_cmd = DeleteMemoryCommand(customer_id=customer_id, reason="GDPR erasure request", actor="dpo_admin")
    async with uow.begin(async_session):
        deleted_mem = await delete_handler.handle(async_session, del_cmd, uow=uow)

    assert deleted_mem.is_deleted is True
    assert deleted_mem.deleted_at is not None
    assert deleted_mem.lifecycle_status == LifecycleStatus.SOFT_DELETED

    # 3. Restore
    restore_cmd = RestoreMemoryCommand(customer_id=customer_id, reason="Customer opted back in", actor="support_lead")
    async with uow.begin(async_session):
        restored_mem = await restore_handler.handle(async_session, restore_cmd, uow=uow)

    assert restored_mem.is_deleted is False
    assert restored_mem.deleted_at is None
    assert restored_mem.lifecycle_status == LifecycleStatus.ACTIVE

    # Verify events
    published = publisher.get_published_events()
    assert any(isinstance(e, MemoryDeletedDomainEvent) for e in published)
    assert any(isinstance(e, MemoryRestoredDomainEvent) for e in published)


# ── 7. Command Bus Idempotency & Safe Retries ────────────────────────────────

@pytest.mark.asyncio
async def test_command_bus_idempotency_deduplication(async_session: AsyncSession):
    """Test that submitting duplicate command with the same Idempotency-Key returns cached result."""
    customer_id = uuid4()
    customer = Customer(id=customer_id, phone="+919876543216", name="Idempotent Customer")
    async_session.add(customer)
    await async_session.commit()

    bus = MemoryCommandBus()
    idempotency_key = "idemp-key-" + str(uuid4())

    cmd = CreateMemoryCommand(
        customer_id=customer_id,
        memory_payload={"personal_info": {"full_name": "Idempotent User"}},
        idempotency_key=idempotency_key,
    )

    # First execution -> executes create
    res1 = await bus.execute(async_session, cmd)
    await async_session.commit()
    assert res1.customer_id == customer_id

    # Second execution with same idempotency_key -> returns cached result without re-executing
    res2 = await bus.execute(async_session, cmd)
    res2_id = res2["id"] if isinstance(res2, dict) else res2.id
    assert str(res2_id) == str(res1.id)


# ── 8. Unit of Work Rollback on Validation Failure ───────────────────────────

@pytest.mark.asyncio
async def test_unit_of_work_atomicity_and_rollback(async_session: AsyncSession):
    """Test that validation failure in handler rolls back transaction cleanly without leaving orphaned records."""
    customer_id = uuid4()
    # Note: Customer is intentionally NOT added to session -> PersistenceValidator will fail

    publisher = MemoryEventPublisher()
    uow = MemoryUnitOfWork(event_publisher=publisher)
    handler = CreateMemoryHandler()

    command = CreateMemoryCommand(
        customer_id=customer_id,
        memory_payload={"personal_info": {"full_name": "Ghost Customer"}},
    )

    with pytest.raises(MemoryValidationError):
        async with uow.begin(async_session):
            await handler.handle(async_session, command, uow=uow)

    # Verify no domain events were published
    assert len(publisher.get_published_events()) == 0


# ── 9. REST API Integration Tests (PATCH, PUT, Concurrency ETag, Status Endpoints) ──

@pytest.mark.asyncio
async def test_rest_api_lifecycle_and_concurrency_endpoints(async_session: AsyncSession):
    """Test full HTTP API lifecycle operations including PUT, PATCH, ETag If-Match, 412, and 423 status codes."""
    app = create_app()

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        customer_id = uuid4()
        customer = Customer(id=customer_id, phone="+919876543299", name="REST API User")
        async_session.add(customer)
        await async_session.commit()

        # 1. POST /api/v1/memory (Create)
        create_resp = await client.post(
            "/api/v1/memory",
            json={
                "customer_id": str(customer_id),
                "memory_payload": {
                    "personal_info": {"full_name": "REST API User", "location": {"city": "Hyderabad"}},
                    "financial_info": {"budget_max": 4000000.0},
                },
            },
            headers={"X-Idempotency-Key": f"idemp-create-{customer_id}"},
        )
        assert create_resp.status_code == 201
        create_data = create_resp.json()
        assert create_data["version_number"] == 1
        etag = create_resp.headers.get("ETag")
        assert etag is not None

        # 2. PATCH /api/v1/memory/{customer_id} with valid If-Match
        patch_resp = await client.patch(
            f"/api/v1/memory/{customer_id}",
            json={"memory_payload": {"financial_info": {"budget_max": 6500000.0}}},
            headers={"If-Match": etag},
        )
        assert patch_resp.status_code == 200
        patch_data = patch_resp.json()
        assert patch_data["version_number"] == 2
        assert patch_data["memory_payload"]["financial_info"]["budget_max"] == 6500000.0
        assert patch_data["memory_payload"]["personal_info"]["full_name"] == "REST API User"
        new_etag = patch_resp.headers.get("ETag")
        assert new_etag != etag

        # 3. PATCH /api/v1/memory/{customer_id} with stale If-Match -> 412 Precondition Failed
        stale_patch = await client.patch(
            f"/api/v1/memory/{customer_id}",
            json={"memory_payload": {"financial_info": {"budget_max": 9900000.0}}},
            headers={"If-Match": etag},  # Using old etag!
        )
        assert stale_patch.status_code == 412
        assert "concurrency" in stale_patch.json()["detail"].lower()

        # 4. PUT /api/v1/memory/{customer_id} (Full Replace)
        put_resp = await client.put(
            f"/api/v1/memory/{customer_id}",
            json={
                "memory_payload": {
                    "personal_info": {"full_name": "REST API User Overwritten"},
                    "identity": {"tags": ["vip_replaced"]},
                }
            },
            headers={"If-Match": new_etag},
        )
        assert put_resp.status_code == 200
        put_data = put_resp.json()
        assert put_data["version_number"] == 3
        assert put_data["memory_payload"]["financial_info"]["budget_max"] is None
        assert put_data["memory_payload"]["personal_info"]["full_name"] == "REST API User Overwritten"
        assert put_data["memory_payload"]["identity"]["tags"] == ["vip_replaced"]
        v3_etag = put_resp.headers.get("ETag")

        # 5. POST /api/v1/memory/{customer_id}/status -> LOCK
        lock_resp = await client.post(
            f"/api/v1/memory/{customer_id}/status",
            json={"target_status": "LOCKED", "reason": "Administrative freeze"},
        )
        assert lock_resp.status_code == 200
        assert lock_resp.json()["lifecycle_status"] == "LOCKED"

        # 6. Attempt PATCH while LOCKED -> 423 Locked
        locked_patch = await client.patch(
            f"/api/v1/memory/{customer_id}",
            json={"memory_payload": {"identity": {"tags": ["hacked"]}}},
            headers={"If-Match": v3_etag},
        )
        assert locked_patch.status_code == 423

        # 7. POST /api/v1/memory/{customer_id}/status -> ACTIVE (Unlock)
        unlock_resp = await client.post(
            f"/api/v1/memory/{customer_id}/status",
            json={"target_status": "ACTIVE", "reason": "Administrative unfreeze"},
        )
        assert unlock_resp.status_code == 200
        assert unlock_resp.json()["lifecycle_status"] == "ACTIVE"

        # 8. DELETE /api/v1/memory/{customer_id} (Soft Delete)
        del_resp = await client.delete(f"/api/v1/memory/{customer_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["is_deleted"] is True

        # 9. POST /api/v1/memory/{customer_id}/restore
        restore_resp = await client.post(
            f"/api/v1/memory/{customer_id}/restore",
            json={"reason": "Customer reactivated"},
        )
        assert restore_resp.status_code == 200
        assert restore_resp.json()["is_deleted"] is False
        assert restore_resp.json()["lifecycle_status"] == "ACTIVE"

    app.dependency_overrides.clear()
