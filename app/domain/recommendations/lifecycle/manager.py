from __future__ import annotations
from datetime import datetime
from app.domain.recommendations.lifecycle.models import RecommendationLifecycleState, RecommendationLifecycleTransition

class RecommendationLifecycleError(Exception):
    """Raised when an invalid lifecycle transition is attempted."""
    pass

class RecommendationLifecycleManager:
    # Defined valid transitions
    VALID_TRANSITIONS = {
        RecommendationLifecycleState.CANDIDATE: {
            RecommendationLifecycleState.ACTIVE,
            RecommendationLifecycleState.DISMISSED,
            RecommendationLifecycleState.EXPIRED
        },
        RecommendationLifecycleState.ACTIVE: {
            RecommendationLifecycleState.ACKNOWLEDGED,
            RecommendationLifecycleState.DISMISSED,
            RecommendationLifecycleState.EXPIRED,
            RecommendationLifecycleState.FULFILLED
        },
        RecommendationLifecycleState.ACKNOWLEDGED: {
            RecommendationLifecycleState.FULFILLED,
            RecommendationLifecycleState.DISMISSED
        },
        RecommendationLifecycleState.DISMISSED: set(),
        RecommendationLifecycleState.EXPIRED: set(),
        RecommendationLifecycleState.FULFILLED: set(),
    }

    @classmethod
    def can_transition(
        cls, current_state: RecommendationLifecycleState, next_state: RecommendationLifecycleState
    ) -> bool:
        return next_state in cls.VALID_TRANSITIONS.get(current_state, set())

    @classmethod
    def transition(
        cls,
        current_state: RecommendationLifecycleState,
        next_state: RecommendationLifecycleState,
        reason: str | None = None,
        actor: str | None = None
    ) -> RecommendationLifecycleTransition:
        if not cls.can_transition(current_state, next_state):
            raise RecommendationLifecycleError(
                f"Invalid transition from {current_state.value} to {next_state.value}"
            )
        
        return RecommendationLifecycleTransition(
            from_state=current_state,
            to_state=next_state,
            timestamp=datetime.utcnow(),
            reason=reason,
            actor=actor
        )
