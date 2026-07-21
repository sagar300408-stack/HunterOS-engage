from abc import ABC, abstractmethod
from typing import List, Type
from enum import Enum

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
    async def publish(self, event: UniversalBaseEvent) -> None:
        """
        Publish an event to all interested consumers.
        This operation must be non-blocking from the publisher's perspective.
        """
        pass
