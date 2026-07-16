from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.integration.repository import IntegrationRepository
from app.domain.integration.engine import IntegrationEngine
from app.domain.integration.schemas import IntegrationConnectionResponse, ConnectRequest, ConnectorMetadata
from app.domain.integration.credentials import JsonCredentialProvider

router = APIRouter(prefix="/integration", tags=["integration"])


def get_integration_engine(request: Request, db: AsyncSession = Depends(get_db)) -> IntegrationEngine:
    # Phase 9.1: Using JsonCredentialProvider. 
    # In future, this could inject a KMS/Vault provider.
    cred_provider = JsonCredentialProvider()
    return IntegrationEngine(session=db, cred_provider=cred_provider, event_bus=request.app.state.event_bus)


@router.get("/available", response_model=List[ConnectorMetadata])
async def get_available_connectors(engine: IntegrationEngine = Depends(get_integration_engine)):
    """
    List all available connectors in the marketplace.
    """
    return engine.get_available_connectors()


@router.get("/workspace/{workspace_id}/connections", response_model=List[IntegrationConnectionResponse])
async def get_active_connections(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    List all active connections for a workspace.
    """
    repo = IntegrationRepository(db)
    return await repo.get_active_connections_by_workspace(workspace_id)


@router.post("/workspace/{workspace_id}/connect", response_model=IntegrationConnectionResponse)
async def connect_provider(
    workspace_id: UUID, 
    req: ConnectRequest, 
    engine: IntegrationEngine = Depends(get_integration_engine)
):
    """
    Establish a new integration connection.
    """
    try:
        connection = await engine.connect_provider(
            workspace_id=workspace_id,
            connector_id=req.connector_id,
            name=req.name,
            credentials=req.credentials,
            settings=req.settings
        )
        return connection
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connection/{connection_id}/disconnect")
async def disconnect_provider(
    connection_id: UUID, 
    engine: IntegrationEngine = Depends(get_integration_engine)
):
    """
    Disconnects a provider, clearing its credentials.
    """
    try:
        await engine.disconnect_provider(connection_id)
        return {"status": "success", "message": "Disconnected successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
