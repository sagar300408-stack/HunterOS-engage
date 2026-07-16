from app.domain.timeline.repository import TimelineRepository
from app.domain.timeline.service import TimelineProjection
from app.domain.analytics.repository import AnalyticsRepository
from app.domain.analytics.service import AnalyticsProjection
from app.domain.livestream.service import LiveStreamProjection

from app.events.bus.event_bus import EventBus
from app.events.projections.manager import ProjectionManager

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
    
    # 2. Register Projection Framework (Priority 50)
    projection_manager = ProjectionManager()
    
    #   2a. Timeline Projection
    timeline_repo = TimelineRepository()
    timeline_projection = TimelineProjection(timeline_repo)
    projection_manager.register_projection(timeline_projection)
    
    #   2b. Analytics Projection
    analytics_repo = AnalyticsRepository()
    analytics_projection = AnalyticsProjection(analytics_repo)
    projection_manager.register_projection(analytics_projection)
    
    #   2c. Live Stream Projection
    livestream_projection = LiveStreamProjection()
    projection_manager.register_projection(livestream_projection)
    
    # Register the single projection manager consumer to the event bus
    event_bus.register_consumer(projection_manager)
