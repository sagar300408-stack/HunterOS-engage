from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import jwt

from app.core.config import settings
from app.integrations.postgres.database import get_db
from app.domain.security.models import User
from app.domain.security.engines.authentication import AuthenticationEngine
from app.domain.security.engines.authorization import AuthorizationEngine

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Validates the JWT token and retrieves the current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = AuthenticationEngine.decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    stmt = select(User).where(User.id == user_id, User.is_active == "true")
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    return user


class RequirePermissions:
    """
    Dependency generator for enforcing RBAC on specific endpoints.
    Usage:
        @router.get("/", dependencies=[Depends(RequirePermissions("view_all"))])
    """
    def __init__(self, *required_permissions: str):
        self.required_permissions = required_permissions

    def __call__(self, current_user: User = Depends(get_current_user)):
        for permission in self.required_permissions:
            if not AuthorizationEngine.role_can(current_user.role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required: {permission}"
                )
        return current_user
