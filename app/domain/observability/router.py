from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.integrations.postgres.database import get_db
from app.domain.observability.models import Alert, Incident
from app.api.v1.auth_deps import get_current_user, RequirePermissions
from app.api.v1.security import verify_internal_network

router = APIRouter(tags=["Observability"])

@router.get("/metrics", dependencies=[Depends(verify_internal_network)])
async def get_metrics():
    """
    Exposes Prometheus metrics for scraping.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/api/v1/alerts", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_alerts(db: AsyncSession = Depends(get_db)):
    """
    List all active observability alerts.
    """
    stmt = select(Alert).where(Alert.status == "active").order_by(Alert.severity.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/api/v1/incidents", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_incidents(db: AsyncSession = Depends(get_db)):
    """
    List all ongoing incidents.
    """
    stmt = select(Incident).where(Incident.status != "resolved").order_by(Incident.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
