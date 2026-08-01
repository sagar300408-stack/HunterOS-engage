import uuid
from typing import List, Type

import pytest
import pytest_asyncio

from app.events.bus.event_bus import EventBus
from app.events.bus.exceptions import ConsumerRegistrationError
from app.events.bus.interfaces import EventConsumer
from app.events.registry.registry import ConsumerRegistry
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
    for ev in consumer.get_subscriptions():
        registry.register(ev, consumer)

    subscribers = registry.get_consumers(CustomerRepliedEvent)
    assert consumer in subscribers


def test_registry_inheritance_routing():
    registry = ConsumerRegistry()
    
    specific_consumer = DummyCustomerRepliedConsumer()
    category_consumer = DummyConversationCategoryConsumer()
    high_priority_consumer = DummyHighPriorityConsumer()
    
    for ev in specific_consumer.get_subscriptions():
        registry.register(ev, specific_consumer)
    for ev in category_consumer.get_subscriptions():
        registry.register(ev, category_consumer)
    for ev in high_priority_consumer.get_subscriptions():
        registry.register(ev, high_priority_consumer)

    subscribers = registry.get_consumers(CustomerRepliedEvent)
    
    assert high_priority_consumer in subscribers
    assert specific_consumer in subscribers
    assert category_consumer in subscribers






