"""
Auth API — Login endpoint.

POST /api/v1/auth/login   → returns JWT access token
GET  /api/v1/auth/me      → returns current user profile
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth_deps import get_current_user
from app.domain.security.models import User
from app.domain.dashboard.schemas import LoginRequest, TokenResponse, UserSchema
from app.domain.dashboard.service import authenticate_user, create_access_token
from app.integrations.postgres.database import get_db
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
logger = get_logger(__name__)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Dashboard Login",
    description="Authenticate with email + password, receive a JWT Bearer token.",
)
async def login(
    req: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await authenticate_user(session, req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    await session.commit()

    logger.info(
        "user_login_success",
        email=user.email,
        role=user.role,
        ip=request.client.host if request.client else "unknown",
    )

    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        full_name=user.full_name,
        workspace_id=str(user.workspace_id),
    )


@router.get(
    "/me",
    response_model=UserSchema,
    summary="Current User Profile",
)
async def get_me(user: User = Depends(get_current_user)) -> UserSchema:
    return UserSchema.model_validate(user)
