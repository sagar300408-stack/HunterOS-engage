from app.domain.timeline.consumer import TimelineConsumer
from app.domain.timeline.repository import TimelineRepository
from app.domain.timeline.service import TimelineProjectionEngine
from app.events.bus.event_bus import EventBus
from app.events.store.consumer import EventStoreConsumer
from app.events.store.repository import EventStoreRepository
from app.events.store.service import EventStoreService


def bootstrap_event_consumers(event_bus: EventBus):
    """
    Central bootstrap location for registering all operational and projection consumers 
    with the HunterOS Event Bus.
    """
    
    # 1. Register Event Store (Priority 100)
    store_repo = EventStoreRepository()
    store_service = EventStoreService(store_repo)
    event_store_consumer = EventStoreConsumer(store_service)
    
    event_bus.register_consumer(event_store_consumer)
    
    # 2. Register Timeline Projection (Priority 50)
    timeline_repo = TimelineRepository()
    timeline_engine = TimelineProjectionEngine(timeline_repo)
    timeline_consumer = TimelineConsumer(timeline_engine)
    
    event_bus.register_consumer(timeline_consumer)
    
    # Future consumers (Analytics, Audit, Notifications, etc.) will be registered here.
