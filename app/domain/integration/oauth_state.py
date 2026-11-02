import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from app.config import get_settings
from app.domain.reliability.engines.caching import get_redis
import redis.asyncio as aioredis

logger = logging.getLogger("hunteros.integration.oauth_state")

OAUTH_STATE_KEY_PREFIX = "oauth_state:"
DEFAULT_STATE_TTL_SECONDS = 600  # 10 minutes

# Atomic GETDEL Lua script ensuring single-use consumption even on pre-6.2 Redis
_LUA_ATOMIC_GETDEL = """
local val = redis.call('GET', KEYS[1])
if val then
    redis.call('DEL', KEYS[1])
end
return val
"""


class OAuthStateError(Exception):
    """Base exception for OAuth state errors."""
    pass


class OAuthStateStorageError(OAuthStateError):
    """Raised when Redis operations for OAuth state fail (preventing insecure fallback)."""
    pass


class OAuthStateManager:
    """
    Manages OAuth CSRF state parameters stored in Redis.
    Provides atomic generation, validation, and single-use consumption.
    Binds state cryptographically to initiating user and workspace.
    """

    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self._redis = redis_client

    def _get_client(self) -> aioredis.Redis:
        if self._redis is not None:
            return self._redis
        try:
            return get_redis()
        except Exception as e:
            logger.error(f"Failed to obtain Redis client for OAuth state: {e}")
            raise OAuthStateStorageError(f"Redis unavailable: {e}")

    async def create_state(
        self,
        workspace_id: UUID,
        integration_id: UUID,
        provider: str,
        user_id: Optional[UUID] = None,
        ttl_seconds: int = DEFAULT_STATE_TTL_SECONDS,
    ) -> str:
        """
        Generates a cryptographically random state token and persists the session binding in Redis.
        """
        state_token = secrets.token_urlsafe(32)
        key = f"{OAUTH_STATE_KEY_PREFIX}{state_token}"
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        
        payload = {
            "workspace_id": str(workspace_id),
            "integration_id": str(integration_id),
            "provider": provider,
            "user_id": str(user_id) if user_id else None,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        
        client = self._get_client()
        try:
            await client.set(key, json.dumps(payload), ex=ttl_seconds)
            logger.info(
                f"Stored OAuth state in Redis (provider={provider}, workspace_id={workspace_id}, ttl={ttl_seconds}s)"
            )
            return state_token
        except Exception as e:
            logger.error(f"Failed to write OAuth state to Redis: {e}")
            raise OAuthStateStorageError(f"Failed to persist OAuth state in Redis: {e}")

    async def consume_state(self, state_token: str) -> Optional[Dict[str, Any]]:
        """
        Atomically retrieves and deletes the OAuth state record from Redis.
        Ensures strict single-use consumption to prevent replay attacks.
        Returns None if state is invalid, expired, or already consumed.
        """
        if not state_token:
            return None

        key = f"{OAUTH_STATE_KEY_PREFIX}{state_token}"
        client = self._get_client()

        try:
            # First attempt native GETDEL (Redis 6.2+)
            try:
                raw_val = await client.getdel(key)
            except (aioredis.ResponseError, AttributeError):
                # Fallback to atomic Lua script
                raw_val = await client.eval(_LUA_ATOMIC_GETDEL, 1, key)

            if not raw_val:
                logger.warning(f"OAuth state lookup failed or already consumed: {state_token[:8]}...")
                return None

            data = json.loads(raw_val)
            
            # Double check expiration timestamp if present in payload
            if "expires_at" in data:
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.now(timezone.utc) > expires_at:
                    logger.warning(f"OAuth state expired at {expires_at}: {state_token[:8]}...")
                    return None

            logger.info(f"OAuth state successfully consumed: {state_token[:8]}...")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Corrupted OAuth state JSON in Redis: {e}")
            return None
        except Exception as e:
            logger.error(f"Redis error during OAuth state consumption: {e}")
            raise OAuthStateStorageError(f"Redis error during OAuth state consumption: {e}")

    async def peek_state(self, state_token: str) -> Optional[Dict[str, Any]]:
        """
        Reads state without consuming it (useful for inspection/tests).
        """
        if not state_token:
            return None
        key = f"{OAUTH_STATE_KEY_PREFIX}{state_token}"
        client = self._get_client()
        try:
            raw_val = await client.get(key)
            if not raw_val:
                return None
            return json.loads(raw_val)
        except Exception as e:
            raise OAuthStateStorageError(f"Redis error: {e}")


# Singleton state manager instance
default_state_manager = OAuthStateManager()
