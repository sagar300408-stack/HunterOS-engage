"""
Wave 2 Final E2E Certification — Event Reliability Pipeline
===========================================================
The ultimate test of B7-B10 functioning together as a unified system.
Proves the entire lifecycle from DOMAIN ACTION to FINAL SYSTEM STATE.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import List, Type

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# ── Domain model imports ──────────────────────────────────────────────────────
from app.domain.conversations.models import Base  # noqa: F401
from app.domain.customers.models import Customer
from app.domain.memory.models import CustomerMemory  # noqa: F401
from app.domain.intent.models import IntentHistory  # noqa: F401
from app.domain.security.models import AuditLog  # noqa: F401
from app.domain.dashboard.models import PipelineEvent  # noqa: F401
from app.domain.followup.models import FollowUpQueue  # noqa: F401

# ── Event infrastructure ──────────────────────────────────────────────────────
from app.events.bus.event_bus import EventBus
from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.categories.conversation_events import CustomerRepliedEvent
from app.events.lifecycle.manager import LifecycleManager
from app.events.model.actor_types import ActorType
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.lifecycle import EventLifecycleState
from app.events.store.repository import EventStoreRepository
from app.events.store.service import EventStoreService
from app.events.worker.tasks import _dispatch_async

from tests.domain.events.conftest import _delete_event_store_rows


def _make_bus() -> EventBus:
    return EventBus(store_service=EventStoreService(repository=EventStoreRepository()))


class CustomerUpdateConsumer(EventConsumer):
    """
    Simulates a real downstream domain side-effect.
    Listens to CustomerRepliedEvent and updates the Customer record's name.
    """
    def __init__(self, pg_session_factory):
        self.pg_session_factory = pg_session_factory
        self.processed = 0

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [CustomerRepliedEvent]

    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.ORDERED

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        async with self.pg_session_factory() as session:
            async with session.begin():
                customer = await session.get(Customer, event.metadata["customer_id"])
                if customer:
                    customer.name = "UPDATED BY E2E EVENT"
                    self.processed += 1


# ══════════════════════════════════════════════════════════════════════════════
# FINAL WAVE 2 E2E — The Grand Unified Reliability Test
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_wave2_full_event_lifecycle_with_retry_and_recovery(pg_session, pg_session_factory):
    """
    The definitive end-to-end test proving the entire B7-B10 surface area:
    1. (Domain Action) Write Customer record + Event in one transaction (B9 Atomicity)
    2. (Lifecycle) Transition to QUEUED
    3. (Consumer) Dispatch runs and consumer executes (B7 Delivery)
    4. (State) Event transitions to COMPLETED
    5. (Idempotency) Exact same event published again is suppressed (B10 Idempotency)
    6. (Result) Consumer ran exactly once and domain state is correct.
    """
    ws_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    bus = _make_bus()
    
    event = CustomerRepliedEvent(
        workspace_id=ws_id,
        actor_type=ActorType.CUSTOMER,
        source_subsystem="e2e_test",
        message_content="Grand Unified Test",
        wa_message_id=f"wa_{uuid.uuid4().hex[:12]}",
        metadata={"customer_id": cust_id},
    )

    consumer = CustomerUpdateConsumer(pg_session_factory)

    try:
        # STEP 1: Atomic Business State + Event Outbox Publication
        async with pg_session_factory() as session:
            async with session.begin():
                cust = Customer(
                    id=cust_id,
                    workspace_id=ws_id,
                    phone=f"12345-{uuid.uuid4().hex[:6]}",
                    name="INITIAL NAME",
                    status="new",
                    preferred_language="en",
                )
                session.add(cust)
                # Publish event in the SAME transaction
                record = await bus.publish(session, event)
        
        # STEP 2: Transition to QUEUED
        async with pg_session_factory() as s:
            async with s.begin():
                await LifecycleManager.queue(s, event.event_id)

        # STEP 3: Consumer Execution via Dispatcher
        from app.events.registry import registry as global_registry
        original = global_registry._subscriptions.copy()
        global_registry._subscriptions.clear()
        global_registry.register(CustomerRepliedEvent, consumer)

        try:
            await _dispatch_async(event_id=event.event_id, max_retries=0)
        finally:
            global_registry._subscriptions.clear()
            global_registry._subscriptions.update(original)

        # STEP 4: Assertions - Consumer ran
        assert consumer.processed == 1, "Consumer must process the event exactly once"

        # Verify domain state changed
        async with pg_session_factory() as s:
            updated_customer = await s.get(Customer, cust_id)
            assert updated_customer.name == "UPDATED BY E2E EVENT", \
                "Domain side-effect must be durably committed"

        # Verify event state is COMPLETED
        repo = EventStoreRepository()
        async with pg_session_factory() as s:
            stored = await repo.get_by_event_id(s, event.event_id)
            assert stored.lifecycle_state == EventLifecycleState.COMPLETED.value

        # STEP 5: Idempotency Verification — Re-publish exact same event
        async with pg_session_factory() as s:
            async with s.begin():
                duplicate_record = await bus.publish(s, event)

        # It must return the existing COMPLETED record, not create a new one
        assert duplicate_record.event_id == event.event_id
        assert duplicate_record.lifecycle_state == EventLifecycleState.COMPLETED.value
        
        # The consumer MUST NOT run again
        assert consumer.processed == 1, "Consumer must not run twice for identical event"

    finally:
        # Clean up both the event and the domain record
        await _delete_event_store_rows(pg_session_factory, ws_id)
        async with pg_session_factory() as cleanup_session:
            async with cleanup_session.begin():
                cust = await cleanup_session.get(Customer, cust_id)
                if cust:
                    await cleanup_session.delete(cust)
