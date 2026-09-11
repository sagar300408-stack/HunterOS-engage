import pytest
import uuid
import json
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus.event_bus import EventBus
from app.events.store.service import EventStoreService
from app.events.store.repository import EventStoreRepository
from app.events.worker.tasks import _dispatch_async
from app.events.model.lifecycle import EventLifecycleState
from app.events.lifecycle.manager import LifecycleManager
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.actor_types import ActorType
from app.events.model.categories import EventCategory
from app.integrations.websocket.manager import ws_manager
from app.domain.ui.consumer import UIEventConsumer
from app.events.registry import registry as global_registry
from unittest.mock import patch

from app.domain.customers.models import Customer
from fastapi import WebSocket

from tests.domain.events.conftest import _delete_event_store_rows


def _make_bus() -> EventBus:
    return EventBus(store_service=EventStoreService(repository=EventStoreRepository()))


class DummyCustomerUpdatedEvent(UniversalBaseEvent):
    category: EventCategory = EventCategory.CUSTOMER
    event_name: str = "customer_updated"


@pytest.mark.asyncio
@patch("app.domain.reliability.engines.caching.get_redis")
async def test_b12_websocket_delivery_via_outbox(mock_get_redis, pg_session: AsyncSession, pg_session_factory):
    """
    B12 VERIFICATION:
    Proves that:
    1. A domain event is published to the Outbox.
    2. Dispatcher processes the event.
    3. UIEventConsumer translates it to a UI DTO.
    4. Event is broadcast strictly to connected websockets matching the workspace_id.
    """
    ws_id = uuid.uuid4()
    other_ws_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    
    mock_redis = AsyncMock()
    mock_get_redis.return_value = None
    
    # We create two distinct mock websockets
    ws_mock_auth = AsyncMock(spec=WebSocket)
    ws_mock_auth.client = ("127.0.0.1", 12345)
    ws_mock_auth.state = type('obj', (object,), {})()
    
    ws_mock_foreign = AsyncMock()
    ws_mock_foreign.client = ("127.0.0.1", 12346)
    ws_mock_foreign.state = type('obj', (object,), {})()
    
    # Connect them via ws_manager (B12 workspace scoping)
    await ws_manager.connect(ws_mock_auth, workspace_id=ws_id)
    await ws_manager.connect(ws_mock_foreign, workspace_id=other_ws_id)
    
    # 2. Setup the event
    bus = _make_bus()
    event = DummyCustomerUpdatedEvent(
        workspace_id=ws_id,
        customer_id=customer_id,
        actor_type=ActorType.SYSTEM,
        source_subsystem="b12_test",
        metadata={"name": "Alice Tested"}
    )
    
    try:
        # STEP 1: Publish to Outbox
        async with pg_session_factory() as session:
            async with session.begin():
                record = await bus.publish(session, event)
                
        # STEP 2: Transition to QUEUED
        async with pg_session_factory() as s:
            async with s.begin():
                await LifecycleManager.queue(s, event.event_id)

        # STEP 3: Register Consumer & Dispatch
        consumer = UIEventConsumer()
        original_subs = global_registry._subscriptions.copy()
        global_registry._subscriptions.clear()
        
        # UIEventConsumer listens to UniversalBaseEvent (all events)
        global_registry.register(UniversalBaseEvent, consumer)

        try:
            await _dispatch_async(event_id=event.event_id, max_retries=0)
        finally:
            global_registry._subscriptions.clear()
            global_registry._subscriptions.update(original_subs)
            
        # STEP 4: Verify WebSocket Delivery Isolation
        # The authorized websocket should have received it exactly once
        assert ws_mock_auth.send_text.call_count == 1, "Authorized client must receive exactly 1 message"
        
        msg_payload = ws_mock_auth.send_text.call_args[0][0]
        msg_dict = json.loads(msg_payload)
        
        # Verify the translated UI DTO
        assert msg_dict["event"] == "customer_updated"
        assert msg_dict["data"]["customer_id"] == str(customer_id)
        assert msg_dict["data"]["customer_name"] == "Alice Tested"
        assert "timestamp" in msg_dict
        
        # The foreign websocket must NEVER receive the event
        assert ws_mock_foreign.send_text.call_count == 0, "Foreign workspace client MUST NOT receive the event (Workspace Isolation breached)"
        
    finally:
        # Cleanup
        ws_manager.disconnect(ws_mock_auth)
        ws_manager.disconnect(ws_mock_foreign)
        await _delete_event_store_rows(pg_session_factory, ws_id)
