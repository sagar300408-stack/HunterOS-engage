import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.database import get_db
import app.domain.conversations.models
from app.domain.customers.models import Customer
from app.domain.memory import (
    CreateMemoryCommand,
    CustomerMemory,
    CustomerMemoryTimelineEvent,
    CustomerMemoryVersion,
    MemoryChangeLog,
    MemoryIdempotencyRecord,
    MemoryUnitOfWork,
    UpdateMemoryCommand,
)
from app.domain.memory.commands.create_memory import CreateMemoryHandler
from app.domain.memory.commands.update_memory import UpdateMemoryHandler


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


@pytest.mark.asyncio
async def test_database_level_race_condition(async_session: AsyncSession, session_maker):
    """
    Test concurrent updates using two independent AsyncSessions against the same record.
    Commit Writer A first, then attempt Writer B using the stale revision.
    """
    customer_id = uuid4()
    
    # 1. Setup baseline using the main session
    customer = Customer(id=customer_id, phone="+919876543000", name="Concurrent Customer")
    async_session.add(customer)
    await async_session.commit()

    uow_main = MemoryUnitOfWork()
    create_handler = CreateMemoryHandler()
    create_cmd = CreateMemoryCommand(
        customer_id=customer_id, 
        memory_payload={"personal_info": {"full_name": "Initial"}}
    )
    async with uow_main.begin(async_session):
        mem_v1 = await create_handler.handle(async_session, create_cmd, uow=uow_main)
    
    v1_revision = mem_v1.revision_id
    assert mem_v1.version_number == 1
    
    update_handler = UpdateMemoryHandler()
    
    cmd_A = UpdateMemoryCommand(
        customer_id=customer_id,
        memory_payload={"personal_info": {"full_name": "Writer A Update"}},
        expected_revision_id=v1_revision,
        actor="Writer_A",
        changed_module="Writer A Module"
    )
    
    cmd_B = UpdateMemoryCommand(
        customer_id=customer_id,
        memory_payload={"personal_info": {"full_name": "Writer B Update"}},
        expected_revision_id=v1_revision,
        actor="Writer_B",
        changed_module="Writer B Module"
    )

    # 2. Independent sessions
    session_A = session_maker()
    session_B = session_maker()
    
    # 3. Simulate Race Condition: Both sessions fetch the record concurrently
    mem_A = await update_handler.read_repo.get_by_customer_id(session_A, customer_id)
    mem_B = await update_handler.read_repo.get_by_customer_id(session_B, customer_id)
    
    assert mem_A.revision_id == v1_revision
    assert mem_B.revision_id == v1_revision
    
    # 4. Writer A applies changes and commits
    old_payload_A = mem_A.update_payload(
        delta_payload=cmd_A.memory_payload,
        source=cmd_A.changed_module,
        actor=cmd_A.actor,
        expected_revision_id=cmd_A.expected_revision_id,
    )
    await update_handler.write_repo.update(session_A, mem_A)
    await update_handler.audit_service.record_update_audit(
        session=session_A,
        memory=mem_A,
        old_payload=old_payload_A,
        new_payload=mem_A.memory_payload,
        actor=cmd_A.actor,
        changed_module=cmd_A.changed_module,
    )
    await session_A.commit()
    
    # 5. Writer B applies changes to its stale instance and attempts to commit
    old_payload_B = mem_B.update_payload(
        delta_payload=cmd_B.memory_payload,
        source=cmd_B.changed_module,
        actor=cmd_B.actor,
        expected_revision_id=cmd_B.expected_revision_id,
    )
    await update_handler.write_repo.update(session_B, mem_B)
    await update_handler.audit_service.record_update_audit(
        session=session_B,
        memory=mem_B,
        old_payload=old_payload_B,
        new_payload=mem_B.memory_payload,
        actor=cmd_B.actor,
        changed_module=cmd_B.changed_module,
    )
    
    # The actual commit where the DB race condition occurs
    try:
        await session_B.commit()
    except Exception as e:
        # We expect a database OCC error like StaleDataError here
        pass
    
    await session_A.close()
    await session_B.close()
    
    # 6. Verify final database state
    async with session_maker() as session_verify:
        final_mem = await update_handler.read_repo.get_by_customer_id(session_verify, customer_id)
        
        # Check that ONLY Writer A's changes persisted
        if final_mem.version_number == 3 or final_mem.memory_payload["personal_info"]["full_name"] == "Writer B Update":
            pytest.fail("Race condition detected: Writer B successfully committed stale data, overwriting Writer A without DB-level OCC check!")
            
        assert final_mem.version_number == 2
        assert final_mem.memory_payload["personal_info"]["full_name"] == "Writer A Update"
        
        # Verify no artifacts from Writer B leaked
        change_logs, _ = await update_handler.read_repo.get_change_logs(session_verify, customer_id, page=1, page_size=100)
        
        for log in change_logs:
            if log.changed_by == "Writer_B":
                pytest.fail("Race condition detected: Writer B's changelog leaked into the database!")
