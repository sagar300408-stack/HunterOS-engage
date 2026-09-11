import uuid
from pydantic import Field
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.integration_types import IntegrationType

class IntegrationConnected(UniversalBaseEvent):
    event_category: EventCategory = Field(default=EventCategory.INTEGRATION)
    connector_id: str
    connector_type: str

class IntegrationDisconnected(UniversalBaseEvent):
    event_category: EventCategory = Field(default=EventCategory.INTEGRATION)
    connector_id: str
    connector_type: str
