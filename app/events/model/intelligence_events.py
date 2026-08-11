from uuid import UUID
from app.events.model.base_event import UniversalBaseEvent


class RecommendationCreatedEvent(UniversalBaseEvent):
    """
    Emitted when a Recommendation is successfully created in Phase 2.
    Serves as the trigger for Phase 3.2 Action Intelligence.
    """
    workspace_id: UUID
    recommendation_id: UUID
    recommendation_type: str
    status: str


class RecommendationUpdatedEvent(UniversalBaseEvent):
    """
    Emitted when a Recommendation is updated in Phase 2.
    """
    workspace_id: UUID
    recommendation_id: UUID
    status: str
