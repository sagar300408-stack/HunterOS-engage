from __future__ import annotations
from typing import Any

from app.domain.recommendations.lifecycle.models import RecommendationLifecycleState
from app.domain.recommendations.lifecycle.manager import RecommendationLifecycleManager

class RecommendationValidator:
    @staticmethod
    def validate_workspace_isolation(workspace_id: str | None, expected_workspace_id: str) -> None:
        if not workspace_id:
            raise ValueError("Workspace ID is required for recommendation isolation.")
        if workspace_id != expected_workspace_id:
            raise ValueError(f"Workspace mismatch: expected {expected_workspace_id}, got {workspace_id}")

    @staticmethod
    def validate_confidence(confidence_score: float) -> None:
        if not (0.0 <= confidence_score <= 1.0):
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {confidence_score}")

    @staticmethod
    def validate_target_identity(target_id: str | None, target_type: str | None) -> None:
        if not target_id or not target_type:
            raise ValueError("Both target_id and target_type must be provided.")

    @staticmethod
    def validate_timestamp_ordering(created_at: Any, updated_at: Any) -> None:
        if created_at and updated_at and updated_at < created_at:
            raise ValueError("updated_at cannot be earlier than created_at.")

    @staticmethod
    def validate_lifecycle_transition(
        current_state: RecommendationLifecycleState, next_state: RecommendationLifecycleState
    ) -> None:
        if not RecommendationLifecycleManager.can_transition(current_state, next_state):
            raise ValueError(f"Invalid lifecycle transition from {current_state} to {next_state}.")
