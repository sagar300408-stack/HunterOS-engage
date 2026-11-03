import logging
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth_deps import RequirePermissions, get_current_user
from app.config import get_settings
from app.domain.integration.credentials import (
    EncryptedCredentialProvider,
    JsonCredentialProvider,
    get_credential_provider,
)
from app.domain.integration.engines.gateway import IntegrationGateway
from app.domain.integration.engines.sync import SynchronizationEngine
from app.domain.integration.models import ConnectionStatus, IntegrationConnection, SyncJob
from app.domain.integration.oauth_state import (
    OAuthStateManager,
    OAuthStateStorageError,
    default_state_manager,
)
from app.domain.integration.schemas import (
    ConnectRequest,
    EmailAuthorizeResponse,
    EmailIntegrationStatusResponse,
    IntegrationConnectionResponse,
    UpdateIntegrationRequest,
)
from app.domain.security.models import User
from app.integrations.postgres.database import get_db

logger = logging.getLogger("hunteros.integration.router")

router = APIRouter(prefix="/integrations", tags=["Integrations"])

# ── Scopes Configuration ──────────────────────────────────────────────────────

# P0-4: Minimum scopes required for Google Calendar + Gmail integration
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
GOOGLE_GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GOOGLE_GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

GOOGLE_OAUTH_SCOPES = [
    GOOGLE_CALENDAR_SCOPE,
    GOOGLE_GMAIL_READONLY_SCOPE,
    GOOGLE_GMAIL_SEND_SCOPE,
]

REQUIRED_GOOGLE_SCOPES = set(GOOGLE_OAUTH_SCOPES)

# P0-5: Minimum delegated permissions required for Microsoft Calendar + Mail
MICROSOFT_OFFLINE_ACCESS_SCOPE = "offline_access"
MICROSOFT_CALENDAR_SCOPE = "Calendars.ReadWrite"
MICROSOFT_MAIL_READ_SCOPE = "Mail.Read"
MICROSOFT_MAIL_SEND_SCOPE = "Mail.Send"
MICROSOFT_USER_READ_SCOPE = "User.Read"

MICROSOFT_OAUTH_SCOPES = [
    MICROSOFT_OFFLINE_ACCESS_SCOPE,
    MICROSOFT_CALENDAR_SCOPE,
    MICROSOFT_MAIL_READ_SCOPE,
    MICROSOFT_MAIL_SEND_SCOPE,
    MICROSOFT_USER_READ_SCOPE,
]

REQUIRED_MICROSOFT_SCOPES = {
    MICROSOFT_CALENDAR_SCOPE,
    MICROSOFT_MAIL_READ_SCOPE,
    MICROSOFT_MAIL_SEND_SCOPE,
}

# Legacy backward-compatibility symbol
OAUTH_STATE_CACHE: Dict[str, Any] = {}


def get_oauth_state_manager() -> OAuthStateManager:
    """FastAPI dependency for injecting OAuthStateManager."""
    return default_state_manager


# ── P0-3: Strict Workspace Isolation Operations ───────────────────────────────

@router.get("", response_model=List[IntegrationConnectionResponse])
async def list_integrations(
    user: User = Depends(RequirePermissions("view_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all configured integrations for the authenticated tenant workspace.
    Enforces strict workspace boundary.
    """
    stmt = (
        select(IntegrationConnection)
        .where(IntegrationConnection.workspace_id == user.workspace_id)
        .order_by(IntegrationConnection.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# ── Email Integration Endpoints (E1) ──────────────────────────────────────────

@router.get("/email/status", response_model=List[EmailIntegrationStatusResponse])
async def list_email_integrations_status(
    user: User = Depends(RequirePermissions("view_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the status of all email integrations connected to the authenticated workspace.
    Explicitly filters by workspace_id and ensures NO credentials or tokens are exposed.
    """
    stmt = (
        select(IntegrationConnection)
        .where(
            IntegrationConnection.workspace_id == user.workspace_id,
            (IntegrationConnection.connector_type == "email")
            | (IntegrationConnection.provider.in_(["google", "microsoft"])),
        )
        .order_by(IntegrationConnection.created_at.desc())
    )
    result = await db.execute(stmt)
    connections = result.scalars().all()

    responses = []
    for conn in connections:
        settings = conn.settings or {}
        responses.append(
            EmailIntegrationStatusResponse(
                id=conn.id,
                workspace_id=conn.workspace_id,
                provider=conn.provider,
                connector_id=conn.connector_id,
                name=conn.name,
                status=conn.status,
                email=settings.get("email"),
                display_name=settings.get("display_name"),
                last_sync_at=conn.last_sync_at,
                error_message=conn.error_message,
                created_at=conn.created_at,
                updated_at=conn.updated_at,
            )
        )
    return responses


@router.get("/email/{provider}/authorize", response_model=EmailAuthorizeResponse)
async def email_authorize(
    provider: str,
    request: Request,
    user: User = Depends(RequirePermissions("edit_all")),
    db: AsyncSession = Depends(get_db),
    state_manager: OAuthStateManager = Depends(get_oauth_state_manager),
):
    """
    Initiates email provider OAuth authorization for the authenticated workspace.
    Supports 'google' and 'microsoft'.
    Creates a pending integration connection if one does not already exist,
    generates a secure state in Redis, and returns the provider's authorization URL.
    """
    provider_norm = provider.lower().strip()
    if provider_norm not in ["google", "microsoft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported email provider: '{provider}'. Supported: google, microsoft.",
        )

    connector_id = "google_gmail_v1" if provider_norm == "google" else "outlook_mail_v1"
    default_name = "Google Gmail" if provider_norm == "google" else "Microsoft Outlook"

    # Check for existing pending connection or create new pending connection
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.workspace_id == user.workspace_id,
        IntegrationConnection.connector_id == connector_id,
        IntegrationConnection.status == ConnectionStatus.PENDING.value,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()

    if not connection:
        connection = IntegrationConnection(
            id=uuid.uuid4(),
            workspace_id=user.workspace_id,
            connector_id=connector_id,
            connector_type="email",
            provider=provider_norm,
            name=default_name,
            status=ConnectionStatus.PENDING.value,
            credentials_json={},
            settings={},
        )
        db.add(connection)
        await db.commit()
        try:
            await db.refresh(connection)
        except Exception:
            pass

    # Generate state in Redis
    try:
        state_token = await state_manager.create_state(
            workspace_id=user.workspace_id,
            integration_id=connection.id,
            provider=provider_norm,
            user_id=user.id,
            ttl_seconds=600,
        )
    except OAuthStateStorageError as e:
        logger.error(f"Failed to persist email OAuth state in Redis: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth state storage unavailable: {e}",
        )

    settings = get_settings()
    redirect_uri = settings.google_redirect_uri if provider_norm == "google" else settings.microsoft_redirect_uri
    if not redirect_uri:
        redirect_uri = str(request.url_for("oauth_callback")) if request else "http://testserver/callback"

    from app.domain.integration.email_auth.provider import get_email_oauth_provider
    oauth_provider = get_email_oauth_provider(provider_norm, tenant_id=settings.microsoft_tenant_id)

    client_id = settings.google_client_id if provider_norm == "google" else settings.microsoft_client_id
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Client ID for {provider_norm} is not configured.",
        )

    auth_url = oauth_provider.get_authorization_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state_token=state_token,
    )

    return EmailAuthorizeResponse(
        authorize_url=auth_url,
        connection_id=connection.id,
        provider=provider_norm,
        state=state_token,
    )


@router.get("/{integration_id}", response_model=IntegrationConnectionResponse)
async def get_integration(
    integration_id: uuid.UUID,
    user: User = Depends(RequirePermissions("view_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a single integration by ID, strictly scoped to the user's workspace.
    Returns 404 if not found or belongs to another workspace.
    """
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == user.workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration connection not found",
        )
    return connection


@router.post("", response_model=IntegrationConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    req: ConnectRequest,
    user: User = Depends(RequirePermissions("edit_all")),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """
    Creates and connects an integration explicitly for the authenticated workspace.
    Credentials are encrypted before persistence.
    """
    from app.domain.integration.engine import IntegrationEngine
    from app.domain.integration.connectors.registry import connector_registry

    event_bus = getattr(request.app.state, "event_bus", None) if request else None
    if not event_bus:
        from app.events.bus.event_bus import EventBus
        event_bus = EventBus(db)

    cred_provider = EncryptedCredentialProvider()
    engine = IntegrationEngine(db, cred_provider=cred_provider, event_bus=event_bus)

    try:
        connection = await engine.connect_provider(
            workspace_id=user.workspace_id,
            connector_id=req.connector_id,
            name=req.name,
            credentials=req.credentials,
            settings=req.settings,
        )
        return connection
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{integration_id}", response_model=IntegrationConnectionResponse)
async def update_integration(
    integration_id: uuid.UUID,
    req: UpdateIntegrationRequest,
    user: User = Depends(RequirePermissions("edit_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates integration metadata/settings strictly within the user's workspace.
    """
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == user.workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration connection not found",
        )

    if req.name is not None:
        connection.name = req.name
    if req.settings is not None:
        connection.settings = req.settings

    await db.commit()
    await db.refresh(connection)
    return connection


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: uuid.UUID,
    user: User = Depends(RequirePermissions("edit_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnects and deletes an integration within the user's workspace.
    Wipes stored encrypted credentials.
    """
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == user.workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration connection not found",
        )

    cred_provider = EncryptedCredentialProvider()
    cred_provider.clear_credentials(connection)
    connection.status = ConnectionStatus.DISCONNECTED.value
    await db.commit()
    return {"status": "success", "message": "Integration disconnected successfully"}


@router.post("/{integration_id}/disconnect")
async def disconnect_integration(
    integration_id: uuid.UUID,
    user: User = Depends(RequirePermissions("edit_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnects an integration within the user's workspace.
    Wipes stored encrypted credentials and sets status to DISCONNECTED.
    """
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == user.workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration connection not found",
        )

    cred_provider = EncryptedCredentialProvider()
    cred_provider.clear_credentials(connection)
    connection.status = ConnectionStatus.DISCONNECTED.value
    await db.commit()
    return {"status": "success", "message": "Integration disconnected successfully"}


@router.post("/{integration_id}/health-check")
async def check_integration_health(
    integration_id: uuid.UUID,
    user: User = Depends(RequirePermissions("view_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates connection health against upstream provider.
    Scoped strictly to authenticated user's workspace.
    Attempts automatic token refresh if token expired.
    """
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == user.workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration connection not found",
        )

    cred_provider = EncryptedCredentialProvider()
    creds = cred_provider.retrieve_credentials(connection)

    from app.domain.integration.connectors.registry import connector_registry
    connector = connector_registry.get_connector(connection.connector_id)
    if not connector:
        connector = connector_registry.get_connector_for_provider(connection.provider)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No connector registered for {connection.connector_id or connection.provider}",
        )

    status_val, err_msg = await connector.health_check(creds, connection.settings or {})
    connection.status = status_val
    connection.error_message = err_msg
    await db.commit()

    return {
        "integration_id": str(connection.id),
        "status": status_val,
        "healthy": status_val == ConnectionStatus.CONNECTED.value,
        "error": err_msg,
    }


@router.post("/{integration_id}/refresh")
async def refresh_integration_token(
    integration_id: uuid.UUID,
    user: User = Depends(RequirePermissions("edit_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    Forces a manual refresh of the OAuth access token.
    Uses distributed Redis locking and updates connection status.
    """
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == user.workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration connection not found",
        )

    from app.domain.integration.email_auth.manager import EmailTokenManager
    from app.domain.integration.email_auth.provider import EmailOAuthError, OAuthReauthRequiredError

    cred_provider = EncryptedCredentialProvider()
    token_mgr = EmailTokenManager(db=db, cred_provider=cred_provider)

    try:
        updated_creds = await token_mgr.refresh_token(connection)
        return {
            "integration_id": str(connection.id),
            "status": "success",
            "connection_status": connection.status,
            "message": "Token refreshed successfully",
        }
    except OAuthReauthRequiredError as e:
        logger.warning(f"Re-authorization required for connection {connection.id}: {e}")
        return {
            "integration_id": str(connection.id),
            "status": "reauth_required",
            "connection_status": ConnectionStatus.REAUTH_REQUIRED.value,
            "message": str(e),
        }
    except EmailOAuthError as e:
        logger.error(f"Failed to refresh token for connection {connection.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token refresh failed: {e}",
        )


@router.post("/{integration_id}/webhook")
async def webhook_receiver(
    integration_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Public webhook receiver for an external vendor integration.
    """
    return await IntegrationGateway.process_webhook(db, integration_id, request)


@router.post("/{integration_id}/sync", dependencies=[Depends(RequirePermissions("edit_all"))])
async def trigger_manual_sync(
    integration_id: uuid.UUID,
    user: User = Depends(RequirePermissions("edit_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually triggers an incremental sync, verifying tenant ownership.
    """
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == user.workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration connection not found",
        )

    job = await SynchronizationEngine.trigger_incremental_sync(db, integration_id)
    return {"job_id": str(job.id), "status": job.status}


@router.get("/{integration_id}/jobs", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_sync_jobs(
    integration_id: uuid.UUID,
    user: User = Depends(RequirePermissions("view_all")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns sync history for a connector belonging strictly to the user's workspace.
    """
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == user.workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration connection not found",
        )

    stmt_jobs = select(SyncJob).where(SyncJob.integration_id == integration_id).order_by(SyncJob.started_at.desc())
    result_jobs = await db.execute(stmt_jobs)
    return result_jobs.scalars().all()


# ── P0-2, P0-4, P0-5: Secure Redis-Backed OAuth Flow with Email Scopes ─────────

@router.get("/{integration_id}/oauth/authorize")
async def oauth_authorize(
    integration_id: uuid.UUID,
    request: Request,
    workspace_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(RequirePermissions("edit_all")),
    state_manager: OAuthStateManager = Depends(get_oauth_state_manager),
):
    """
    P0-2, P0-3, P0-4, P0-5:
    - Generates a cryptographically secure random OAuth state and stores it in Redis with 10-minute TTL.
    - Strictly validates tenant workspace ownership (never trusts mismatched client query params).
    - Google authorization URL includes both Calendar and Gmail scopes.
    - Microsoft authorization URL includes both Calendar and Mail delegated permissions.
    """
    # 1. Strict server-side workspace isolation
    if isinstance(user, User):
        effective_workspace_id = user.workspace_id
        if workspace_id is not None and workspace_id != user.workspace_id:
            logger.warning(
                f"Cross-workspace OAuth authorize attempt rejected: user_ws={user.workspace_id}, param_ws={workspace_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workspace mismatch: cannot access integrations of another workspace",
            )
    elif workspace_id is not None:
        # Fallback for direct testing calls without auth dependency context
        effective_workspace_id = workspace_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace ID required",
        )

    # 2. Query connection bound to workspace
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == effective_workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration connection not found",
        )

    # 3. P0-2: Store state in Redis
    mgr = state_manager or default_state_manager
    try:
        state_token = await mgr.create_state(
            workspace_id=effective_workspace_id,
            integration_id=integration_id,
            provider=connection.provider,
            user_id=user.id if isinstance(user, User) else None,
            ttl_seconds=600,
        )
    except OAuthStateStorageError as e:
        logger.error(f"Failed to persist OAuth state in Redis: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth state storage unavailable: {e}",
        )

    # Populate legacy cache for backward compatibility with older tests if needed
    OAUTH_STATE_CACHE[state_token] = {
        "workspace_id": effective_workspace_id,
        "integration_id": integration_id,
        "expires_at": datetime.now(timezone.utc),
    }

    settings = get_settings()
    redirect_uri = str(request.url_for("oauth_callback")) if request else "http://testserver/callback"

    # 4. P0-4 & P0-5: Generate Provider Authorization URL with required scopes
    auth_url = ""
    if connection.provider == "google":
        client_id = settings.google_client_id or connection.settings.get("client_id")
        if not client_id:
            raise HTTPException(status_code=400, detail="Google client_id is not configured")

        # P0-4: Calendar + Gmail readonly + Gmail send scopes
        google_scopes = " ".join(GOOGLE_OAUTH_SCOPES)
        params = {
            "client_id": client_id,
            "response_type": "code",
            "scope": google_scopes,
            "redirect_uri": redirect_uri,
            "state": state_token,
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    elif connection.provider == "microsoft":
        client_id = settings.microsoft_client_id or connection.settings.get("client_id")
        if not client_id:
            raise HTTPException(status_code=400, detail="Microsoft client_id is not configured")

        # P0-5: Calendar + Mail read + Mail send + User read + offline access
        microsoft_scopes = " ".join(MICROSOFT_OAUTH_SCOPES)
        params = {
            "client_id": client_id,
            "response_type": "code",
            "scope": microsoft_scopes,
            "redirect_uri": redirect_uri,
            "state": state_token,
            "prompt": "consent",
        }
        auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {connection.provider}")

    return {"authorize_url": auth_url}


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    state: str,
    code: str,
    db: AsyncSession = Depends(get_db),
    state_manager: OAuthStateManager = Depends(get_oauth_state_manager),
):
    """
    P0-1, P0-2, P0-3, P0-4, P0-5:
    - Atomically validates and consumes the state token from Redis (single-use consumption prevents replay).
    - Extracts workspace and integration identity strictly from server-validated state.
    - Validates that granted scopes include the required permissions (detects missing scopes).
    - Stores credentials using authenticated encryption (Fernet).
    """
    mgr = state_manager or default_state_manager

    # 1. P0-2: Atomic consumption from Redis (GETDEL)
    try:
        cache_entry = await mgr.consume_state(state)
    except OAuthStateStorageError as e:
        logger.error(f"Redis error during OAuth callback state consumption: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth state service unavailable: {e}",
        )

    # Clean legacy cache if populated
    OAUTH_STATE_CACHE.pop(state, None)

    if not cache_entry:
        logger.warning(f"OAuth callback rejected: Invalid or already consumed state: {state[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    integration_id = UUID(cache_entry["integration_id"])
    workspace_id = UUID(cache_entry["workspace_id"])

    # 2. P0-3: Strict workspace boundary check on integration record
    stmt = select(IntegrationConnection).where(
        IntegrationConnection.id == integration_id,
        IntegrationConnection.workspace_id == workspace_id,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found from state",
        )

    settings = get_settings()
    redirect_uri = (
        settings.google_redirect_uri
        if connection.provider == "google"
        else settings.microsoft_redirect_uri
    )

    if not redirect_uri:
        redirect_uri = str(request.url_for("oauth_callback")) if request else "http://testserver/callback"

    token_url = ""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
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
        logger.error(f"OAuth token exchange failed ({response.status_code}): {response.text}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth exchange failed: {response.text}",
        )

    token_data = response.json()

    # 3. P0-4 & P0-5: Scope validation
    granted_scope_str = token_data.get("scope", "")
    granted_scopes = set(granted_scope_str.split()) if granted_scope_str else set()

    if connection.provider == "google":
        if granted_scopes:
            missing_google = REQUIRED_GOOGLE_SCOPES - granted_scopes
            if missing_google:
                logger.warning(f"Google OAuth granted with missing scopes: {missing_google}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient permissions: Missing required Google scopes: {', '.join(sorted(missing_google))}",
                )
    elif connection.provider == "microsoft":
        if granted_scopes:
            missing_microsoft = REQUIRED_MICROSOFT_SCOPES - granted_scopes
            if missing_microsoft:
                logger.warning(f"Microsoft OAuth granted with missing scopes: {missing_microsoft}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient permissions: Missing required Microsoft scopes: {', '.join(sorted(missing_microsoft))}",
                )

    # 4. P0-1: Store credentials securely using EncryptedCredentialProvider
    cred_provider = EncryptedCredentialProvider()
    cred_provider.store_credentials(connection, token_data)

    connection.status = ConnectionStatus.CONNECTED.value
    new_settings = dict(connection.settings or {})
    if granted_scopes:
        new_settings["granted_scopes"] = list(granted_scopes)

    # E1: Extract account identity from provider and update settings / name
    access_token = token_data.get("access_token")
    if access_token and connection.provider in ["google", "microsoft"]:
        try:
            from app.domain.integration.email_auth.provider import get_email_oauth_provider
            oauth_provider = get_email_oauth_provider(connection.provider, tenant_id=settings.microsoft_tenant_id)
            identity = await oauth_provider.get_account_identity(access_token)
            if identity.get("email"):
                new_settings["email"] = identity["email"]
                new_settings["display_name"] = identity.get("display_name")
                new_settings["provider_account_id"] = identity.get("provider_account_id")
                if identity.get("metadata"):
                    new_settings["identity_metadata"] = identity.get("metadata")

                provider_title = "Google Gmail" if connection.provider == "google" else "Microsoft Outlook"
                if not connection.name or connection.name in ["Google Gmail", "Microsoft Outlook", "Gmail", "Outlook", "Default Connection"]:
                    connection.name = f"{provider_title} ({identity['email']})"
        except Exception as e:
            logger.warning(f"Could not retrieve account identity during OAuth callback: {e}")

    connection.settings = new_settings
    await db.commit()
    logger.info(f"OAuth flow completed securely for integration {integration_id} (workspace={workspace_id})")

    return {"status": "success", "message": "OAuth flow completed securely."}
