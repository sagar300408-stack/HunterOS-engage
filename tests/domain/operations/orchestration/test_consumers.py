"""
Tests for ActionExecutionResultConsumer
"""
import uuid
from unittest.mock import AsyncMock

import pytest

from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType
from app.domain.operations.orchestration.consumers import ActionExecutionResultConsumer


@pytest.mark.asyncio
async def test_consumer_handles_completion():
    mock_orchestration_engine = AsyncMock()
    mock_event_bus = AsyncMock()
    
    consumer = ActionExecutionResultConsumer(mock_orchestration_engine, mock_event_bus)
    
    workspace_id = uuid.uuid4()
    run_id = uuid.uuid4()
    attempt_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    action_id = uuid.uuid4()
    
    event = UniversalBaseEvent(
        workspace_id=workspace_id,
        category=EventCategory.ACTION,
        event_name="action.completed",
        correlation_id=correlation_id,
        metadata={
            "idempotency_key": f"{run_id}:{attempt_id}",
            "action_id": str(action_id),
            "connector_response": {"foo": "bar"}
        },
        actor_type=ActorType.SYSTEM,
        source_subsystem="action_engine"
    )
    
    await consumer.handle_action_completed(event)
    
    mock_orchestration_engine.complete.assert_awaited_once()
    args, kwargs = mock_orchestration_engine.complete.call_args
    assert kwargs["workspace_id"] == workspace_id
    assert kwargs["action_id"] == action_id
    assert kwargs["run_id"] == run_id
    req = kwargs["req"]
    assert req.correlation_id == correlation_id
    import json
    assert req.outcome_data == json.dumps({"foo": "bar"})


@pytest.mark.asyncio
async def test_consumer_handles_failure():
    mock_orchestration_engine = AsyncMock()
    mock_event_bus = AsyncMock()
    
    consumer = ActionExecutionResultConsumer(mock_orchestration_engine, mock_event_bus)
    
    workspace_id = uuid.uuid4()
    run_id = uuid.uuid4()
    attempt_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    action_id = uuid.uuid4()
    
    event = UniversalBaseEvent(
        workspace_id=workspace_id,
        category=EventCategory.ACTION,
        event_name="action.failed",
        correlation_id=correlation_id,
        metadata={
            "idempotency_key": f"{run_id}:{attempt_id}",
            "action_id": str(action_id),
            "error_details": "Something went wrong"
        },
        actor_type=ActorType.SYSTEM,
        source_subsystem="action_engine"
    )
    
    await consumer.handle_action_failed(event)
    
    mock_orchestration_engine.fail.assert_awaited_once()
    args, kwargs = mock_orchestration_engine.fail.call_args
    assert kwargs["workspace_id"] == workspace_id
    assert kwargs["action_id"] == action_id
    assert kwargs["run_id"] == run_id
    req = kwargs["req"]
    assert req.correlation_id == correlation_id
    assert req.failure_reason == "Something went wrong"
    assert req.failure_type == "EXECUTION_FAILED"
    assert req.retryable is True


@pytest.mark.asyncio
async def test_consumer_ignores_invalid_idempotency_key():
    mock_orchestration_engine = AsyncMock()
    mock_event_bus = AsyncMock()
    
    consumer = ActionExecutionResultConsumer(mock_orchestration_engine, mock_event_bus)
    
    event = UniversalBaseEvent(
        workspace_id=uuid.uuid4(),
        category=EventCategory.ACTION,
        event_name="action.completed",
        metadata={
            "idempotency_key": "not-an-orchestration-key", # no colon
            "action_id": str(uuid.uuid4())
        },
        actor_type=ActorType.SYSTEM,
        source_subsystem="action_engine"
    )
    
    await consumer.handle_action_completed(event)
    mock_orchestration_engine.complete.assert_not_awaited()
