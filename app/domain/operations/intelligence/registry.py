from typing import Optional
from app.domain.recommendations.models import RecommendationType
from app.domain.operations.models import ActionType

class ActionCapabilityRegistry:
    """
    Registry for mapping Phase 2 RecommendationTypes to Phase 3.1 ActionTypes.
    This establishes the strict capability boundary.
    Any recommendation type not registered here will be treated as UNSUPPORTED
    and will not result in an Action.
    """
    
    # Hardcoded deterministic capability mapping for V1.
    # We do NOT allow dynamic AI-generated mappings or generic fallbacks.
    _mappings = {
        RecommendationType.FOLLOW_UP: ActionType.CREATE_FOLLOWUP,
        RecommendationType.CONTACT_CUSTOMER: ActionType.SEND_MESSAGE,
        RecommendationType.SCHEDULE_SITE_VISIT: ActionType.SCHEDULE_SITE_VISIT,
    }

    @classmethod
    def get_supported_action(cls, recommendation_type: RecommendationType) -> Optional[ActionType]:
        """
        Returns the mapped ActionType if supported, else None.
        """
        return cls._mappings.get(recommendation_type)

    @classmethod
    def is_supported(cls, recommendation_type: RecommendationType) -> bool:
        return recommendation_type in cls._mappings
