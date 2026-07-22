import uuid
from typing import List, Type

import pytest
import pytest_asyncio

from app.events.bus.event_bus import EventBus
from app.events.bus.exceptions import ConsumerRegistrationError
from app.events.bus.interfaces import EventConsumer
from app.events.bus.registry import ConsumerRegistry
from app.events.categories.conversation_events import ConversationEvent, CustomerRepliedEvent
from app.events.model.actor_types import ActorType
from app.events.model.base_event import UniversalBaseEvent


class DummyCustomerRepliedConsumer(EventConsumer):
    def __init__(self):
        self.received_events = []

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [CustomerRepliedEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        self.received_events.append(event)


class DummyConversationCategoryConsumer(EventConsumer):
    def __init__(self):
        self.received_events = []

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [ConversationEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        self.received_events.append(event)


class DummyHighPriorityConsumer(EventConsumer):
    def __init__(self):
        self.received_events = []

    def get_priority(self) -> int:
        return 100

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [UniversalBaseEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        self.received_events.append(event)


class FailingConsumer(EventConsumer):
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [CustomerRepliedEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        raise ValueError("I always fail!")


def test_registry_registration():
    registry = ConsumerRegistry()
    consumer = DummyCustomerRepliedConsumer()
    registry.register(consumer)

    subscribers = registry.get_subscribers(CustomerRepliedEvent)
    assert consumer in subscribers


def test_registry_inheritance_routing_and_priority():
    registry = ConsumerRegistry()
    
    specific_consumer = DummyCustomerRepliedConsumer()
    category_consumer = DummyConversationCategoryConsumer()
    high_priority_consumer = DummyHighPriorityConsumer()
    
    registry.register(specific_consumer)
    registry.register(category_consumer)
    registry.register(high_priority_consumer)

    subscribers = registry.get_subscribers(CustomerRepliedEvent)
    
    # Priority sorting should place high_priority_consumer first
    assert subscribers[0] == high_priority_consumer
    assert specific_consumer in subscribers
    assert category_consumer in subscribers






