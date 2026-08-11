from __future__ import annotations

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.recommendations.api import RecommendationIntelligenceAPIv1
from app.domain.recommendations.schemas import (
    CreateRecommendationRequest,
    UpdateRecommendationRequest,
    RecommendationDTO,
    ChangeRecommendationStatusRequest,
    RecommendationDetectionResultDTO,
)
from app.domain.recommendations.exceptions import (
    RecommendationNotFoundError,
    RecommendationLifecycleError,
)

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])

def get_api() -> RecommendationIntelligenceAPIv1:
    # Dependency injection placeholder
    raise NotImplementedError

@router.get("/types", response_model=List[str])
def get_types():
    return []

@router.get("/statuses", response_model=List[str])
def get_statuses():
    return []

@router.post("/", response_model=RecommendationDTO, status_code=status.HTTP_201_CREATED)
def create_recommendation(data: CreateRecommendationRequest, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.create_recommendation(data)

@router.get("/", response_model=List[RecommendationDTO])
def list_recommendations(api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.list_recommendations()

@router.get("/workspace/{workspace_id}", response_model=List[RecommendationDTO])
def list_workspace_recommendations(workspace_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.list_recommendations(workspace_id=workspace_id)

@router.get("/customer/{customer_id}", response_model=List[RecommendationDTO])
def list_customer_recommendations(customer_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.list_recommendations(customer_id=customer_id)

@router.get("/{recommendation_id}", response_model=RecommendationDTO)
def get_recommendation(recommendation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    try:
        return api.get_recommendation(recommendation_id)
    except RecommendationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{recommendation_id}", response_model=RecommendationDTO)
def update_recommendation(recommendation_id: UUID, data: UpdateRecommendationRequest, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    try:
        return api.update_recommendation(recommendation_id, data)
    except RecommendationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{recommendation_id}/status", response_model=RecommendationDTO)
def change_status(recommendation_id: UUID, data: ChangeRecommendationStatusRequest, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    try:
        return api.change_status(recommendation_id, data)
    except RecommendationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RecommendationLifecycleError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.post("/detect", response_model=RecommendationDetectionResultDTO)
def detect_recommendations(workspace_id: UUID, target_id: str, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    class DummyTarget: id = target_id
    return api.detect_recommendations(workspace_id, DummyTarget())

@router.post("/detect/customer/{customer_id}", response_model=RecommendationDetectionResultDTO)
def detect_customer_recommendations(customer_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.detect_customer_recommendations(customer_id)

@router.post("/detect/conversation/{conversation_id}", response_model=RecommendationDetectionResultDTO)
def detect_conversation_recommendations(conversation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.detect_conversation_recommendations(conversation_id)

@router.get("/detections/{detection_id}", response_model=RecommendationDetectionResultDTO)
def get_detection_result(detection_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.get_detection_result(detection_id)


@router.post('/prioritize')
def prioritize_recommendations(workspace_id: UUID, target_id: str, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    pass

@router.post('/prioritize/customer/{customer_id}')
def prioritize_customer_recommendations(customer_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    pass

@router.post('/prioritize/conversation/{conversation_id}')
def prioritize_conversation_recommendations(conversation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    pass

@router.get('/prioritization/{result_id}')
def get_prioritization(result_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    pass

@router.post('/explain')
def explain_recommendation(recommendation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.explain_recommendation(recommendation_id)

@router.post('/{recommendation_id}/explain')
def explain_recommendation_by_id(recommendation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.explain_recommendation(recommendation_id)

@router.post('/prioritization/{prioritization_id}/recommendations/{recommendation_id}/explain')
def explain_prioritized_recommendation(prioritization_id: UUID, recommendation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.explain_prioritized_recommendation(prioritization_id, recommendation_id)

@router.get('/explanations/{explanation_id}')
def get_explanation(explanation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.get_explanation(explanation_id)

@router.get('/{recommendation_id}/explanation')
def get_recommendation_explanation(recommendation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.get_recommendation_explanation(recommendation_id)

@router.get('/explanations/{explanation_id}/executive')
def get_executive_explanation(explanation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.get_executive_explanation(explanation_id)

@router.get('/explanations/{explanation_id}/sales')
def get_sales_explanation(explanation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.get_sales_explanation(explanation_id)

@router.get('/explanations/{explanation_id}/operations')
def get_operations_explanation(explanation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.get_operations_explanation(explanation_id)

@router.get('/explanations/{explanation_id}/audit')
def get_audit_explanation(explanation_id: UUID, api: RecommendationIntelligenceAPIv1 = Depends(get_api)):
    return api.get_audit_explanation(explanation_id)
