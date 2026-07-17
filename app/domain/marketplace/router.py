from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.marketplace.schemas import (
    ConnectorDefinitionSchema, InstalledConnectorSchema, ConnectorHealthRecordSchema,
    InstallConnectorRequest, ConfigureConnectorRequest, UpgradeConnectorRequest
)
from app.domain.marketplace.engine import MarketplaceEngine
from app.domain.marketplace.repository import MarketplaceRepository
from app.domain.marketplace.registry import ConnectorCapabilityRegistry

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def get_marketplace_engine(request: Request, db: AsyncSession = Depends(get_db)) -> MarketplaceEngine:
    return MarketplaceEngine(session=db, event_bus=request.app.state.event_bus)


def get_marketplace_registry(db: AsyncSession = Depends(get_db)) -> ConnectorCapabilityRegistry:
    repo = MarketplaceRepository(session=db)
    return ConnectorCapabilityRegistry(repo=repo)


@router.get("/connectors", response_model=List[ConnectorDefinitionSchema])
async def browse_connectors(engine: MarketplaceEngine = Depends(get_marketplace_engine)):
    return await engine.list_available_connectors()


@router.post("/workspaces/{workspace_id}/installations", response_model=InstalledConnectorSchema)
async def install_connector(
    workspace_id: UUID,
    req: InstallConnectorRequest,
    engine: MarketplaceEngine = Depends(get_marketplace_engine)
):
    try:
        return await engine.install_connector(workspace_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/workspaces/{workspace_id}/installations/{installation_id}/configure", response_model=InstalledConnectorSchema)
async def configure_connector(
    workspace_id: UUID,
    installation_id: UUID,
    req: ConfigureConnectorRequest,
    engine: MarketplaceEngine = Depends(get_marketplace_engine)
):
    try:
        return await engine.configure_connector(workspace_id, installation_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspaces/{workspace_id}/installations/{installation_id}/enable", response_model=InstalledConnectorSchema)
async def enable_connector(
    workspace_id: UUID,
    installation_id: UUID,
    engine: MarketplaceEngine = Depends(get_marketplace_engine)
):
    try:
        return await engine.enable_connector(workspace_id, installation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspaces/{workspace_id}/installations/{installation_id}/disable", response_model=InstalledConnectorSchema)
async def disable_connector(
    workspace_id: UUID,
    installation_id: UUID,
    engine: MarketplaceEngine = Depends(get_marketplace_engine)
):
    try:
        return await engine.disable_connector(workspace_id, installation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspaces/{workspace_id}/installations/{installation_id}/upgrade", response_model=InstalledConnectorSchema)
async def upgrade_connector(
    workspace_id: UUID,
    installation_id: UUID,
    req: UpgradeConnectorRequest,
    engine: MarketplaceEngine = Depends(get_marketplace_engine)
):
    try:
        return await engine.upgrade_connector(workspace_id, installation_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
