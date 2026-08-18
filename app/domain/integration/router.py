from typing import List
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
from datetime import datetime, timedelta
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


from app.config import get_settings
import httpx
from app.domain.integration.credentials import JsonCredentialProvider

# ── O2/O3: Secure OAuth Flow ──────────────────────────────────────────────────

# In-memory temporary cache for OAuth states (Phase 9 implementation without Redis dependency)
# Format: state_token -> {"workspace_id": UUID, "integration_id": UUID, "expires_at": datetime}
OAUTH_STATE_CACHE = {}

@router.get("/{integration_id}/oauth/authorize")
async def oauth_authorize(
    integration_id: uuid.UUID, 
    workspace_id: uuid.UUID, # Extracted from auth middleware typically
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a secure OAuth state parameter and stores it in cache.
    Returns the authorization URL.
    """
    stmt = select(IntegrationConnection).where(IntegrationConnection.id == integration_id, IntegrationConnection.workspace_id == workspace_id)
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Integration connection not found")

    state_token = secrets.token_urlsafe(32)
    
    # Store in temporary cache for 15 minutes
    # Using timezone-aware datetime to fix pytest warnings
    OAUTH_STATE_CACHE[state_token] = {
        "workspace_id": workspace_id,
        "integration_id": integration_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    
    settings = get_settings()
    redirect_uri = str(request.url_for("oauth_callback"))
    
    auth_url = ""
    if connection.provider == "google":
        client_id = settings.google_client_id or connection.settings.get("client_id")
        auth_url = (f"https://accounts.google.com/o/oauth2/v2/auth?"
                    f"client_id={client_id}&response_type=code&scope=https://www.googleapis.com/auth/calendar.events&"
                    f"redirect_uri={redirect_uri}&state={state_token}&access_type=offline&prompt=consent")
    elif connection.provider == "microsoft":
        client_id = settings.microsoft_client_id or connection.settings.get("client_id")
        auth_url = (f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
                    f"client_id={client_id}&response_type=code&scope=offline_access Calendars.ReadWrite&"
                    f"redirect_uri={redirect_uri}&state={state_token}&prompt=consent")
    else:
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")
        
    return {"authorize_url": auth_url}


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    state: str,
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Validates the state parameter against the cache before exchanging the code.
    Prevents CSRF attacks.
    """
    cache_entry = OAUTH_STATE_CACHE.get(state)
    
    if not cache_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
        
    if datetime.now(timezone.utc) > cache_entry["expires_at"]:
        del OAUTH_STATE_CACHE[state]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state expired")
        
    integration_id = cache_entry["integration_id"]
    workspace_id = cache_entry["workspace_id"]
    
    # State verified! Clear from cache to prevent replay (single-use consumption)
    del OAUTH_STATE_CACHE[state]
    
    stmt = select(IntegrationConnection).where(IntegrationConnection.id == integration_id, IntegrationConnection.workspace_id == workspace_id)
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Integration not found from state")

    settings = get_settings()
    redirect_uri = str(request.url_for("oauth_callback"))
    
    token_url = ""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }
    
    if connection.provider == "google":
        token_url = "https://oauth2.googleapis.com/token"
        data["client_id"] = settings.google_client_id or connection.settings.get("client_id")
        data["client_secret"] = settings.google_client_secret or connection.settings.get("client_secret")
    elif connection.provider == "microsoft":
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data["client_id"] = settings.microsoft_client_id or connection.settings.get("client_id")
        data["client_secret"] = settings.microsoft_client_secret or connection.settings.get("client_secret")
    else:
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")
        
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {response.text}")
        
    token_data = response.json()
    
    # Store credentials securely using CredentialProvider
    cred_provider = JsonCredentialProvider()
    cred_provider.store_credentials(connection, token_data)
    
    connection.status = "connected"
    await db.commit()
    
    return {"status": "success", "message": "OAuth flow completed securely."}

