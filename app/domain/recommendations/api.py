from __future__ import annotations

from typing import List, Optional, Any
from uuid import UUID

from app.domain.recommendations.engine import RecommendationIntelligenceEngine
from app.domain.recommendations.detection.engine import RecommendationDetectionEngine
from app.domain.recommendations.schemas import (
    RecommendationDTO,
    CreateRecommendationRequest,
    UpdateRecommendationRequest,
    ChangeRecommendationStatusRequest,
    RecommendationDetectionResultDTO,
)

class RecommendationIntelligenceAPIv1:
    """
    Public contract exposing Recommendation Intelligence engine operations.
    Exclusively uses DTOs for communication.
    """
    def __init__(self, engine: RecommendationIntelligenceEngine, detection_engine: RecommendationDetectionEngine = None, explanation_engine: Any = None):
        self.engine = engine
        self.detection_engine = detection_engine
        self.explanation_engine = explanation_engine

    def create_recommendation(self, data: CreateRecommendationRequest) -> RecommendationDTO:
        rec = self.engine.create(data)
        return RecommendationDTO.from_model(rec)

    def get_recommendation(self, recommendation_id: UUID) -> RecommendationDTO:
        rec = self.engine.get(recommendation_id)
        return RecommendationDTO.from_model(rec)

    def update_recommendation(self, recommendation_id: UUID, data: UpdateRecommendationRequest) -> RecommendationDTO:
        rec = self.engine.update(recommendation_id, data)
        return RecommendationDTO.from_model(rec)

    def change_status(self, recommendation_id: UUID, data: ChangeRecommendationStatusRequest) -> RecommendationDTO:
        rec = self.engine.change_status(recommendation_id, data.status, data.reason)
        return RecommendationDTO.from_model(rec)

    def list_recommendations(self, workspace_id: Optional[UUID] = None, customer_id: Optional[UUID] = None) -> List[RecommendationDTO]:
        filters = {}
        if workspace_id:
            filters["workspace_id"] = workspace_id
        if customer_id:
            filters["customer_id"] = customer_id
        recs = self.engine.list(filters)
        return [RecommendationDTO.from_model(r) for r in recs]

    def detect_recommendations(self, workspace_id: UUID, target: Any) -> RecommendationDetectionResultDTO:
        # Context provider and rule registry should ideally be injected, but for the interface:
        result = self.detection_engine.detect(str(workspace_id), target, None, None)
        return RecommendationDetectionResultDTO(
            workspace_id=UUID(result.workspace_id),
            target_id=result.target_id,
            candidates=result.candidates
        )

    def detect_customer_recommendations(self, customer_id: UUID) -> RecommendationDetectionResultDTO:
        class DummyTarget: id = str(customer_id)
        # Using a dummy workspace id
        return self.detect_recommendations(UUID(int=0), DummyTarget())

    def detect_conversation_recommendations(self, conversation_id: UUID) -> RecommendationDetectionResultDTO:
        class DummyTarget: id = str(conversation_id)
        return self.detect_recommendations(UUID(int=0), DummyTarget())

    def prioritize_recommendations(self, workspace_id: UUID, target: Any) -> Any:
        pass

    def prioritize_customer_recommendations(self, customer_id: UUID) -> Any:
        pass

    def prioritize_conversation_recommendations(self, conversation_id: UUID) -> Any:
        pass

    def get_prioritization(self, result_id: UUID) -> Any:
        pass

    def get_customer_prioritization(self, customer_id: UUID) -> Any:
        pass

    def get_priority_view(self, view_id: UUID) -> Any:
        pass

    def get_detection_result(self, detection_id: UUID) -> RecommendationDetectionResultDTO:
        # Mocking retrieval
        return RecommendationDetectionResultDTO(
            workspace_id=UUID(int=0),
            target_id=None,
            candidates=[]
        )

    def explain_recommendation(self, recommendation_id: UUID) -> Any:
        if self.explanation_engine:
            return self.explanation_engine.explain_recommendation(recommendation_id)
        return {}

    def explain_prioritized_recommendation(self, prioritization_id: UUID, recommendation_id: UUID) -> Any:
        if self.explanation_engine:
            return self.explanation_engine.explain_prioritized_recommendation(prioritization_id, recommendation_id)
        return {}

    def get_explanation(self, explanation_id: UUID) -> Any:
        if self.explanation_engine:
            return self.explanation_engine.get_explanation(explanation_id)
        return {}

    def get_recommendation_explanation(self, recommendation_id: UUID) -> Any:
        if self.explanation_engine:
            return self.explanation_engine.get_recommendation_explanation(recommendation_id)
        return {}

    def get_executive_explanation(self, explanation_id: UUID) -> Any:
        if self.explanation_engine:
            return self.explanation_engine.get_executive_explanation(explanation_id)
        return {}

    def get_sales_explanation(self, explanation_id: UUID) -> Any:
        if self.explanation_engine:
            return self.explanation_engine.get_sales_explanation(explanation_id)
        return {}

    def get_operations_explanation(self, explanation_id: UUID) -> Any:
        if self.explanation_engine:
            return self.explanation_engine.get_operations_explanation(explanation_id)
        return {}

    def get_audit_explanation(self, explanation_id: UUID) -> Any:
        if self.explanation_engine:
            return self.explanation_engine.get_audit_explanation(explanation_id)
        return {}
