from __future__ import annotations

import dataclasses
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from app.domain.recommendations.models import Recommendation, RecommendationStatus
from app.domain.recommendations.schemas import (
    CreateRecommendationRequest,
    UpdateRecommendationRequest,
)
from app.domain.recommendations.exceptions import (
    RecommendationNotFoundError,
    RecommendationLifecycleError,
)

class RecommendationIntelligenceEngine:
    """
    Foundation operations for Recommendation Intelligence.
    Handles lifecycle, state transitions, and retrieval.
    Does not implement predictive AI or logic rules.
    Enforces strict immutability.
    """
    def __init__(self, repository: Any):
        self.repository = repository

    def create(self, data: CreateRecommendationRequest) -> Recommendation:
        recommendation = Recommendation(
            id=data.id,
            workspace_id=data.workspace_id,
            customer_id=data.customer_id,
            type=data.type,
            priority=data.priority,
            title=data.title,
            description=data.description,
            status=RecommendationStatus.PROPOSED,
            metadata=data.metadata,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return self.repository.save(recommendation)

    def get(self, recommendation_id: UUID) -> Recommendation:
        recommendation = self.repository.get(recommendation_id)
        if not recommendation:
            raise RecommendationNotFoundError(f"Recommendation {recommendation_id} not found.")
        return recommendation

    def update(self, recommendation_id: UUID, data: UpdateRecommendationRequest) -> Recommendation:
        recommendation = self.get(recommendation_id)
        
        changes = {"updated_at": datetime.now(timezone.utc)}
        if data.title is not None:
            changes["title"] = data.title
        if data.description is not None:
            changes["description"] = data.description
        if data.priority is not None:
            changes["priority"] = data.priority
        if data.metadata is not None:
            changes["metadata"] = data.metadata
            
        updated_recommendation = dataclasses.replace(recommendation, **changes)
        return self.repository.save(updated_recommendation)

    def change_status(self, recommendation_id: UUID, new_status: RecommendationStatus, reason: Optional[str] = None) -> Recommendation:
        recommendation = self.get(recommendation_id)
        
        if recommendation.status == new_status:
            return recommendation
            
        updated_recommendation = dataclasses.replace(
            recommendation,
            status=new_status,
            updated_at=datetime.now(timezone.utc)
        )
        return self.repository.save(updated_recommendation)

    def dismiss(self, recommendation_id: UUID, reason: Optional[str] = None) -> Recommendation:
        return self.change_status(recommendation_id, RecommendationStatus.DISMISSED, reason)

    def acknowledge(self, recommendation_id: UUID) -> Recommendation:
        return self.change_status(recommendation_id, RecommendationStatus.ACKNOWLEDGED)

    def complete(self, recommendation_id: UUID) -> Recommendation:
        return self.change_status(recommendation_id, RecommendationStatus.COMPLETED)

    def expire(self, recommendation_id: UUID) -> Recommendation:
        return self.change_status(recommendation_id, RecommendationStatus.EXPIRED)

    def list(self, filters: Dict[str, Any] = None) -> List[Recommendation]:
        filters = filters or {}
        return self.repository.list(filters)
