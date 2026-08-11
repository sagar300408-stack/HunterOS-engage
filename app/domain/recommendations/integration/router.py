from fastapi import APIRouter
from .api_v1 import api, RecommendationContextDTO

router = APIRouter(prefix="/api/v1/recommendations/integration", tags=["Recommendations Integration"])

@router.get("/{recommendation_id}/full", response_model=RecommendationContextDTO)
async def get_full_context(recommendation_id: str):
    return api.get_full_recommendation_context(recommendation_id)

@router.get("/{recommendation_id}/executive", response_model=RecommendationContextDTO)
async def get_executive_context(recommendation_id: str):
    return api.get_executive_recommendation_context(recommendation_id)
