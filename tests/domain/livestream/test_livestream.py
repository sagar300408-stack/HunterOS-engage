import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import WebSocket

from app.domain.livestream.manager import WebSocketConnectionManager
from app.domain.livestream.service import LiveStreamProjection
from app.events.model.categories import EventCategory
from app.events.categories.conversation_events import CustomerRepliedEvent
from app.events.model.actor_types import ActorType


class MockWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent_messages = []
        self.client = type('Client', (), {'host': '127.0.0.1'})()

    async def accept(self):
        self.accepted = True

    async def send_text(self, data: str):
        self.sent_messages.append(json.loads(data))


@pytest.mark.asyncio
async def test_websocket_manager_workspace_isolation():
    manager = WebSocketConnectionManager()
    workspace_1 = uuid.uuid4()
    workspace_2 = uuid.uuid4()
    
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    await manager.connect(workspace_1, ws1)  # type: ignore
    await manager.connect(workspace_2, ws2)  # type: ignore
    
    assert manager.total_connection_count == 2
    
    # Broadcast to workspace 1
    await manager.broadcast_to_workspace(workspace_1, {"message": "hello w1"})
    
    # Broadcast to workspace 2
    await manager.broadcast_to_workspace(workspace_2, {"message": "hello w2"})
    
    assert len(ws1.sent_messages) == 1
    assert ws1.sent_messages[0]["message"] == "hello w1"
    assert "timestamp" in ws1.sent_messages[0]
    
    assert len(ws2.sent_messages) == 1
    assert ws2.sent_messages[0]["message"] == "hello w2"
    
    # Disconnect
    await manager.disconnect(workspace_1, ws1)  # type: ignore
    assert manager.total_connection_count == 1
    await manager.disconnect(workspace_2, ws2)  # type: ignore
    assert manager.total_connection_count == 0


from unittest.mock import patch

@pytest.mark.asyncio
async def test_livestream_projection():
    # Mock the manager broadcast to avoid actually trying to send anything
    with patch("app.domain.livestream.service.livestream_manager.broadcast_to_workspace") as mock_broadcast:
        projection = LiveStreamProjection()
        assert projection.name == "LiveStreamProjection"
        
        workspace_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        conversation_id = uuid.uuid4()
        
        event = CustomerRepliedEvent(
            workspace_id=workspace_id,
            customer_id=customer_id,
            actor_type=ActorType.CUSTOMER,
            source_subsystem="test",
            conversation_id=conversation_id,
            message_content="Hello world",
            channel="web",
            wa_message_id="msg_123"
        )
        
        await projection.project_event(event, session=None) # type: ignore
        
        mock_broadcast.assert_called_once()
        args, kwargs = mock_broadcast.call_args
        assert args[0] == workspace_id
        payload = args[1]
        
        assert payload["event_type"] == "operational_update"
        assert payload["data"]["category"] == EventCategory.CONVERSATION.value
        assert payload["data"]["name"] == "customer.replied"
        assert payload["data"]["activity_title"] == "Customer replied to conversation"
        assert payload["data"]["customer_id"] == str(customer_id)
        assert payload["data"]["conversation_id"] == str(conversation_id)
