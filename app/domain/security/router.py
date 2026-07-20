from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

from app.integrations.postgres.database import get_db
from app.domain.security.models import User, UserSession, AuditLog
from app.domain.security.engines.authentication import AuthenticationEngine
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
async def login_for_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticates a user and issues a JWT token.
    Records an AuditLog entry for the login attempt.
    """
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not AuthenticationEngine.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if user.is_active != "true":
        raise HTTPException(status_code=400, detail="Inactive user")

    # Generate token
    access_token = AuthenticationEngine.create_access_token(data={"sub": str(user.id)})
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        workspace_id=user.workspace_id,
        user_id=user.id,
        action="login",
        target_type="system",
        target_id=user.id,
        payload={"ip": "unknown"} # Real implementation would read from Request
    )
    db.add(audit)
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "workspace_id": str(current_user.workspace_id)
    }
