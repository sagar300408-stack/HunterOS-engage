"""
Workspace Provisioning API — R7: Real Tenant Provisioning

POST /api/v1/workspaces       — Create and provision a new workspace (platform_admin only)
GET  /api/v1/workspaces/{id}  — Get provisioning status (org_owner of that workspace)

Security:
  - B1: All endpoints require valid JWT authentication
  - Workspace creation: restricted to platform_admin role
  - Workspace status: restricted to platform_admin OR org_owner of that workspace
  - B2: No cross-tenant data exposure
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.postgres.database import get_db
from app.api.v1.auth_deps import get_current_user
from app.domain.security.models import User, UserRole
from app.domain.security.engines.authorization import role_can
from app.domain.onboarding.schemas import WorkspaceProvisionRequest, WorkspaceProvisionResponse
from app.domain.onboarding.engines.workspace import WorkspaceEngine
from app.domain.dashboard.service import hash_password
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/workspaces", tags=["Workspaces"])
logger = get_logger(__name__)


@router.post(
    "",
    response_model=WorkspaceProvisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision Workspace",
    description=(
        "Creates and provisions a new workspace with its required foundational resources. "
        "Idempotent: repeated calls with the same workspace_id converge safely. "
        "Requires platform_admin role."
    ),
)
async def provision_workspace(
    req: WorkspaceProvisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceProvisionResponse:
    """
    R7: Authenticated workspace provisioning endpoint.

    Restricted to platform_admin — this is a platform-level operation.
    B1 authentication is enforced via get_current_user dependency.
    """
    # ── Authorization: platform_admin only ────────────────────────────────────
    if not role_can(current_user.role, "*"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace provisioning requires platform_admin role.",
        )

    # -- Determine workspace_id --
    workspace_id = req.workspace_id or uuid.uuid4()

    logger.info(
        "workspace_provision_requested",
        workspace_id=str(workspace_id),
        owner_email=req.owner_email,
        requested_by=str(current_user.id),
    )

    # -- Run provisioning (idempotent, concurrency-safe) --
    engine = WorkspaceEngine(db)
    provisioning = None
    try:
        provisioning = await engine.provision_workspace(
            workspace_id=workspace_id,
            owner_email=req.owner_email,
            owner_name=req.owner_name,
            password_hash=hash_password(req.owner_password),
        )
    except ValueError as exc:
        # e.g. duplicate email
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(
            "workspace_provisioning_error",
            workspace_id=str(workspace_id),
            error=str(exc),
        )
        current_step = provisioning.current_step if provisioning and hasattr(provisioning, 'current_step') else 'INITIALIZATION'
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Provisioning failed at step '{current_step}': {exc}",
        )

    return WorkspaceProvisionResponse(
        workspace_id=provisioning.workspace_id,
        status=provisioning.status,
        current_step=provisioning.current_step,
        created_at=provisioning.created_at,
        completed_at=provisioning.completed_at,
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceProvisionResponse,
    summary="Get Workspace Provisioning Status",
    description="Returns provisioning status for a workspace. Platform admin or workspace owner only.",
)
async def get_workspace_status(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceProvisionResponse:
    """
    Get provisioning status for a workspace.

    Authorization:
      - platform_admin: can see any workspace
      - org_owner: can only see their own workspace (B2 isolation)
    """
    is_admin = role_can(current_user.role, "*")
    is_own_workspace = current_user.workspace_id == workspace_id

    if not is_admin and not is_own_workspace:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: workspace isolation enforced.",
        )

    engine = WorkspaceEngine(db)
    provisioning = await engine.get_provisioning_status(workspace_id)

    if provisioning is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} has not been provisioned.",
        )

    return WorkspaceProvisionResponse(
        workspace_id=provisioning.workspace_id,
        status=provisioning.status,
        current_step=provisioning.current_step,
        created_at=provisioning.created_at,
        completed_at=provisioning.completed_at,
    )
