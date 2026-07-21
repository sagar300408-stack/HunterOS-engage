import asyncio
from typing import List, Any
import logging
import json
from uuid import UUID
from datetime import datetime, timezone

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import select, update

from app.integrations.postgres.database import get_session
from app.events.store.models import EventRecord
from app.events.model.lifecycle import EventLifecycleState
from app.events.bus.interfaces import ExecutionPolicy
from app.events.bus.registry import ConsumerRegistry
from app.events.model.base_event import UniversalBaseEvent

# Temporary dependency logic until proper DI is setup for the worker
_registry: ConsumerRegistry = None

def set_celery_registry(registry: ConsumerRegistry):
    global _registry
    _registry = registry

logger = logging.getLogger(__name__)

async def _mark_dead_letter(event_id: UUID, error_detail: str) -> None:
    async with get_session() as session:
        record = await session.get(EventRecord, event_id)
        if record:
            record.lifecycle_state = EventLifecycleState.DEAD_LETTER.value
            record.error_detail = error_detail
            await session.commit()

async def _dispatch_async(event_id: UUID, current_retry: int, max_retries: int) -> None:
    if not _registry:
        logger.error("ConsumerRegistry not initialized for Celery worker.")
        return

    async with get_session() as session:
        # Load the event record
        record = await session.get(EventRecord, event_id)
        if not record:
            logger.warning(f"EventRecord {event_id} not found. DB transaction might not have committed yet.")
            raise Exception("EventRecord not found (retry needed)")

        # Update lifecycle to PROCESSING
        record.lifecycle_state = EventLifecycleState.PROCESSING.value
        record.processing_started_at = datetime.now(timezone.utc)
        await session.commit()

        # Reconstruct the event model from the payload
        event_dict = record.payload
        event_class = UniversalBaseEvent
        
        for known_class in _registry._subscriptions.keys():
            if known_class.__name__ == record.event_name:
                event_class = known_class
                break
                
        try:
            event = event_class(**event_dict)
        except Exception as e:
            logger.error(f"Failed to deserialize event {event_id}: {e}")
            record.lifecycle_state = EventLifecycleState.FAILED.value
            record.error_detail = str(e)
            await session.commit()
            return

        # Get subscribers
        subscribers = _registry.get_subscribers(event_class)
        
        # Group by execution policy
        ordered_consumers = []
        parallel_consumers = []
        background_consumers = []
        
        for consumer in subscribers:
            policy = consumer.get_execution_policy()
            if policy == ExecutionPolicy.ORDERED:
                ordered_consumers.append(consumer)
            elif policy == ExecutionPolicy.PARALLEL:
                parallel_consumers.append(consumer)
            elif policy == ExecutionPolicy.BACKGROUND:
                background_consumers.append(consumer)
            elif policy == ExecutionPolicy.CRITICAL:
                ordered_consumers.append(consumer)

        has_errors = False
        error_messages = []

        # 1. Execute ORDERED (and CRITICAL) sequentially
        for consumer in ordered_consumers:
            try:
                await consumer.handle_event(event)
            except Exception as e:
                has_errors = True
                error_messages.append(f"{consumer.__class__.__name__}: {str(e)}")
                if consumer.get_execution_policy() == ExecutionPolicy.CRITICAL:
                    break # Abort further processing

        # 2. Execute PARALLEL concurrently
        if parallel_consumers and not has_errors:
            results = await asyncio.gather(
                *[c.handle_event(event) for c in parallel_consumers],
                return_exceptions=True
            )
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    has_errors = True
                    error_messages.append(f"{parallel_consumers[i].__class__.__name__}: {str(result)}")

        # 3. Enqueue BACKGROUND tasks (simulated here by dispatching to another celery task, or just run parallel)
        if background_consumers and not has_errors:
            results = await asyncio.gather(
                *[c.handle_event(event) for c in background_consumers],
                return_exceptions=True
            )
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    has_errors = True
                    error_messages.append(f"{background_consumers[i].__class__.__name__}: {str(result)}")

        # Finalize Lifecycle
        if has_errors:
            record.error_detail = "; ".join(error_messages)
            record.retry_count += 1
            
            if current_retry >= max_retries:
                record.lifecycle_state = EventLifecycleState.DEAD_LETTER.value
            else:
                record.lifecycle_state = EventLifecycleState.FAILED.value
                
            await session.commit()
            raise Exception("Consumer processing failed: " + record.error_detail)
        else:
            record.lifecycle_state = EventLifecycleState.COMPLETED.value
            record.completed_at = datetime.now(timezone.utc)
            await session.commit()


@shared_task(
    bind=True, 
    max_retries=5, 
    default_retry_delay=10,
    queue="event_dispatch",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=30,
    time_limit=60
)
def dispatch_event(self, event_id_str: str):
    """
    Celery task that acts as the Consumer Execution Engine.
    """
    event_id = UUID(event_id_str)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        loop.run_until_complete(_dispatch_async(event_id, self.request.retries, self.max_retries))
    except MaxRetriesExceededError:
        # If Celery runs out of retries, ensure we mark it as DEAD_LETTER
        loop.run_until_complete(_mark_dead_letter(event_id, "Max retries exceeded"))
        raise
    except Exception as exc:
        logger.error(f"Event dispatch failed for {event_id}: {exc}")
        self.retry(exc=exc)
