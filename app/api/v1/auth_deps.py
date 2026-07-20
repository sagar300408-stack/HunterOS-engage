"""
FastAPI Auth Dependencies — RBAC for Dashboard API

Provides two FastAPI dependency functions:
    get_current_user   — validates JWT Bearer token, returns User
    require_permission — validates the user has a specific permission

Usage in routes:
    @router.put("/dashboard/leads/{id}/stage")
    async def move_lead(
        ...,
        user: User = Depends(require_permission("change_lead_stage")),
    ):

Permission strings must match the keys in ROLE_PERMISSIONS (dashboard/models.py):
    "view_all", "edit_memory", "add_note", "change_lead_stage", "*"
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.security.models import User
from app.domain.security.engines.authorization import role_can
from app.domain.dashboard.service import get_user_from_token
from app.integrations.postgres.database import get_db

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate the JWT Bearer token and return the authenticated User.

    Raises HTTP 401 if the token is invalid or expired.
    """
    user = await get_user_from_token(session, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_active != "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    return user


def require_permission(permission: str):
    """
    Factory that returns a FastAPI dependency checking a specific permission.

    Example:
        user = Depends(require_permission("change_lead_stage"))
    """
    async def _check(user: User = Depends(get_current_user)) -> User:
        if not role_can(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your role ({user.role}) does not have permission "
                    f"to perform this action ({permission})."
                ),
            )
        return user
    return _check
