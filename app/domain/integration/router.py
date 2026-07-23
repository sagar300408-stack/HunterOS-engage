from typing import List
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.auth_deps import RequirePermissions
from app.integrations.postgres.database import get_db
from app.domain.integration.models import IntegrationConnection, SyncJob
from app.domain.integration.engines.gateway import IntegrationGateway
from app.domain.integration.engines.sync import SynchronizationEngine

router = APIRouter(prefix="/integrations", tags=["Integrations"])

@router.get("", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_integrations(db: AsyncSession = Depends(get_db)):
    """
    List all configured integrations for the workspace.
    """
    stmt = select(IntegrationConnection)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/{integration_id}/webhook")
async def webhook_receiver(integration_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Public webhook receiver for a specific integration.
    """
    return await IntegrationGateway.process_webhook(db, integration_id, request)

@router.post("/{integration_id}/sync", dependencies=[Depends(RequirePermissions("edit_all"))])
async def trigger_manual_sync(integration_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Manually triggers an incremental sync for an integration.
    """
    job = await SynchronizationEngine.trigger_incremental_sync(db, integration_id)
    return {"job_id": str(job.id), "status": job.status}

@router.get("/{integration_id}/jobs", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_sync_jobs(integration_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns sync history for a connector.
    """
    stmt = select(SyncJob).where(SyncJob.integration_id == integration_id).order_by(SyncJob.started_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
