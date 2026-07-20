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

from app.integrations.postgres.database import get_db
from app.domain.analytics.engines.product_usage import ProductUsageEngine
from app.domain.analytics.engines.customer_health import CustomerHealthEngine
from app.api.deps import RequirePermissions

@router.get("/usage/{workspace_id}", dependencies=[Depends(RequirePermissions("view_all"))])
async def get_usage_metrics(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve DAU/WAU Product Analytics."""
    wau = await ProductUsageEngine.get_active_users(db, workspace_id, days=7)
    return {"weekly_active_users": wau}

@router.get("/customers/{workspace_id}/health", dependencies=[Depends(RequirePermissions("view_all"))])
async def get_customer_health(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve composite customer health score."""
    snapshot = await CustomerHealthEngine.compute_health_snapshot(db, workspace_id)
    return {
        "health_score": snapshot.health_score,
        "renewal_risk": snapshot.renewal_risk,
        "engagement_score": snapshot.engagement_score,
        "adoption_score": snapshot.adoption_score
    }

