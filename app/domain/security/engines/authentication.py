# =============================================================================
# DEPRECATED — Authentication Stabilization Refactor (2026-07-23)
# =============================================================================
# This module is ORPHANED. It is not used by any live route.
#
# The live authentication system uses:
#   - JWT library   : python-jose  (app/domain/dashboard/service.py)
#   - Signing key   : settings.dashboard_secret_key  (app/config.py)
#   - Auth helpers  : authenticate_user(), create_access_token(), get_user_from_token()
#
# This module uses:
#   - JWT library   : PyJWT  (different API surface)
#   - Signing key   : core.config.SECRET_KEY  (a DIFFERENT key — tokens are incompatible)
#
# DO NOT add new imports from this file.
# Scheduled for deletion in the next maintenance sprint.
# =============================================================================

from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

class AuthenticationEngine:
    """
    Handles password hashing and JWT token issuance.
    """
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> dict:
        """
        Decodes token and validates expiration.
        Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
        """
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
