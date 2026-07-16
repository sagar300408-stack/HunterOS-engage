from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Assuming a get_db_session dependency exists in the main app
# from app.database import get_db_session

from app.domain.analytics.repository import AnalyticsRepository
from app.domain.analytics.schemas import AnalyticsMetricResponse
from app.domain.analytics.service import AnalyticsQueryService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

def get_analytics_query_service() -> AnalyticsQueryService:
    repository = AnalyticsRepository()
    return AnalyticsQueryService(repository)

@router.get("/workspace/{workspace_id}", response_model=List[AnalyticsMetricResponse])
async def get_workspace_analytics(
    workspace_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    # session: AsyncSession = Depends(get_db_session),
    service: AnalyticsQueryService = Depends(get_analytics_query_service)
):
    """
    Retrieve aggregated analytics for a workspace.
    """
    session = None
    return await service.get_workspace_metrics(session, workspace_id, start_date, end_date)

@router.get("/customer/{workspace_id}/{customer_id}", response_model=List[AnalyticsMetricResponse])
async def get_customer_analytics(
    workspace_id: UUID,
    customer_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    # session: AsyncSession = Depends(get_db_session),
    service: AnalyticsQueryService = Depends(get_analytics_query_service)
):
    """
    Retrieve aggregated analytics specific to a customer.
    """
    session = None
    return await service.get_customer_metrics(session, workspace_id, customer_id, start_date, end_date)
