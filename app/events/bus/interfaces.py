from abc import ABC, abstractmethod
from typing import List, Optional, Type
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.model.base_event import UniversalBaseEvent

class ExecutionPolicy(str, Enum):
    """
    Dictates how a consumer should be executed by the Event Dispatcher.
    
    ORDERED:    Must run synchronously and sequentially, respecting partition_key.
                Useful for state-machine updates or critical database writes.
    PARALLEL:   Runs concurrently with other consumers via asyncio.gather().
                Good for independent operations.
    BACKGROUND: Sent to a separate Celery queue for slow/background processing.
                Good for AI generation, bulk email, reports, etc.
    CRITICAL:   Fails the entire transaction if it fails.
                (Note: With Transactional Outbox, this usually implies immediate retry)
    """
    ORDERED = "ORDERED"
    PARALLEL = "PARALLEL"
    BACKGROUND = "BACKGROUND"
    CRITICAL = "CRITICAL"


class EventConsumer(ABC):
    """
    Universal interface for all Event Consumers in HunterOS.
    """

    def get_priority(self) -> int:
        """
        Consumers with higher priority are executed first.
        Infrastructure consumers (like EventStore) should return a high priority (e.g. 100).
        Application consumers default to 0.
        """
        return 0
        
    def get_execution_policy(self) -> ExecutionPolicy:
        """
        Returns the execution policy for this consumer.
        Defaults to PARALLEL for maximum throughput.
        """
        return ExecutionPolicy.PARALLEL

    def depends_on(self) -> List[Type["EventConsumer"]]:
        """
        Declares other consumer classes that must execute successfully before
        this consumer is allowed to run.

        The PlanBuilder uses this to construct a DAG and derive topologically-
        sorted execution stages.  Consumers in earlier stages run first;
        consumers in the same stage run concurrently (subject to their
        ExecutionPolicy).

        Rules:
          • A dependency must also be registered for the same event class.
          • Circular dependencies are detected at plan-build time and raise
            PlanValidationFailed.
          • Default is [] (no dependencies) — fully backward-compatible.

        Example:
            class AIConsumer(EventConsumer):
                def depends_on(self):
                    return [WebhookReceiveConsumer]
        """
        return []

    @abstractmethod
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        """
        Returns a list of event classes this consumer is interested in.
        A consumer can subscribe to a specific concrete event (e.g., CustomerRepliedEvent)
        or a base event category (e.g., ConversationEvent).
        """
        pass

    @abstractmethod
    async def handle_event(self, event: UniversalBaseEvent) -> None:
        """
        Process the incoming event. Consumers must handle their own internal errors.
        """
        pass


class EventPublisher(ABC):
    """
    Universal interface for publishing events to the Event Bus.
    """

    @abstractmethod
    async def publish(
        self,
        session: AsyncSession,
        event: UniversalBaseEvent,
        is_replay: bool = False,
    ) -> None:
        """
        Publish an event to the transactional outbox within the given session.
        The session must be active — the caller controls commit/rollback.
        This operation is non-blocking from the publisher's perspective.
        """
        pass
