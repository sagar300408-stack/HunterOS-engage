import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.domain.integration.credentials import (
    CredentialProvider,
    EncryptedCredentialProvider,
    get_credential_provider,
)
from app.domain.integration.email_auth.provider import (
    BaseEmailOAuthProvider,
    OAuthNetworkError,
    OAuthReauthRequiredError,
    OAuthTokenRefreshError,
    get_email_oauth_provider,
)
from app.domain.integration.models import ConnectionStatus, IntegrationConnection
from app.domain.reliability.engines.caching import get_redis
import redis.asyncio as aioredis

logger = logging.getLogger("hunteros.integration.email_auth.manager")


class EmailTokenManager:
    """
    Manages OAuth access and refresh token lifecycles for email provider integrations.
    Handles proactive expiration detection, distributed lock-protected token refreshes,
    re-authentication state transitions, and encrypted persistence.
    """

    LOCK_KEY_PREFIX = "lock:email_token_refresh:"
    DEFAULT_BUFFER_SECONDS = 300  # Proactively refresh if expiring within 5 minutes
    LOCK_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        cred_provider: Optional[CredentialProvider] = None,
        redis_client: Optional[aioredis.Redis] = None,
    ):
        self._db = db
        self._cred_provider = cred_provider or EncryptedCredentialProvider()
        self._redis = redis_client

    def _get_redis(self) -> Optional[aioredis.Redis]:
        if self._redis is not None:
            return self._redis
        try:
            return get_redis()
        except Exception:
            return None

    async def refresh_token(
        self,
        connection: IntegrationConnection,
        session: Optional[AsyncSession] = None,
        provider: Optional[BaseEmailOAuthProvider] = None,
        force_refresh: bool = True,
    ) -> Dict[str, Any]:
        """
        Alias for refresh_connection_tokens using instance db session if not explicitly provided.
        When refresh_token is called directly, force_refresh defaults to True.
        """
        s = session or self._db
        if not s:
            raise ValueError("AsyncSession required for token refresh")
        return await self.refresh_connection_tokens(
            connection=connection,
            session=s,
            provider=provider,
            force_refresh=force_refresh,
        )

    def is_token_expired(self, credentials: Dict[str, Any], buffer_seconds: int = DEFAULT_BUFFER_SECONDS) -> bool:
        """
        Determines whether the access token is expired or will expire within the buffer window.
        """
        if not credentials:
            return True

        cutoff = datetime.now(timezone.utc) + timedelta(seconds=buffer_seconds)

        expires_at_val = credentials.get("expires_at")
        if expires_at_val is not None:
            try:
                if isinstance(expires_at_val, (int, float)):
                    expires_at = datetime.fromtimestamp(expires_at_val, tz=timezone.utc)
                elif isinstance(expires_at_val, datetime):
                    expires_at = expires_at_val if expires_at_val.tzinfo else expires_at_val.replace(tzinfo=timezone.utc)
                elif isinstance(expires_at_val, str):
                    expires_at = datetime.fromisoformat(expires_at_val)
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                else:
                    expires_at = None

                if expires_at:
                    return cutoff >= expires_at
            except Exception:
                pass

        # Fallback using obtained_at and expires_in
        obtained_at_val = credentials.get("obtained_at")
        expires_in = credentials.get("expires_in")
        if obtained_at_val and expires_in:
            try:
                if isinstance(obtained_at_val, (int, float)):
                    obtained_at = datetime.fromtimestamp(obtained_at_val, tz=timezone.utc)
                elif isinstance(obtained_at_val, datetime):
                    obtained_at = obtained_at_val if obtained_at_val.tzinfo else obtained_at_val.replace(tzinfo=timezone.utc)
                else:
                    obtained_at = datetime.fromisoformat(str(obtained_at_val))
                    if obtained_at.tzinfo is None:
                        obtained_at = obtained_at.replace(tzinfo=timezone.utc)
                expires_at = obtained_at + timedelta(seconds=int(expires_in))
                return cutoff >= expires_at
            except Exception:
                pass

        # If credentials has no access_token at all, treat as expired
        if not credentials.get("access_token"):
            return True

        # If no expiration metadata exists but access_token exists, assume token is valid or rely on 401 recovery
        return False

    async def get_valid_credentials(
        self,
        connection: IntegrationConnection,
        session: AsyncSession,
        provider: Optional[BaseEmailOAuthProvider] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieves decrypted credentials, proactively refreshing the access token if expired.
        Uses Redis distributed locking to prevent concurrent token refresh race conditions.
        """
        current_creds = self._cred_provider.retrieve_credentials(connection)

        if not force_refresh and not self.is_token_expired(current_creds):
            return current_creds

        # Token needs refresh
        return await self.refresh_connection_tokens(connection, session, provider=provider, force_refresh=force_refresh)

    async def refresh_connection_tokens(
        self,
        connection: IntegrationConnection,
        session: AsyncSession,
        provider: Optional[BaseEmailOAuthProvider] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Performs distributed-lock protected token refresh.
        Updates credentials, connection status, and database state.
        """
        conn_id_str = str(connection.id)
        lock_key = f"{self.LOCK_KEY_PREFIX}{conn_id_str}"
        redis_client = self._get_redis()
        lock_acquired = False

        # 1. Attempt distributed lock acquisition
        if redis_client:
            try:
                # Try acquiring lock with 30s timeout
                lock_acquired = await redis_client.set(lock_key, "1", nx=True, ex=self.LOCK_TIMEOUT_SECONDS)
                if not lock_acquired:
                    # Another worker is refreshing; wait briefly and re-read from DB
                    logger.info(f"Token refresh lock held for connection {conn_id_str}; awaiting completion...")
                    for _ in range(10):
                        await asyncio.sleep(0.5)
                        # Re-read connection from DB
                        stmt = select(IntegrationConnection).where(IntegrationConnection.id == connection.id)
                        res = await session.execute(stmt)
                        refreshed_conn = res.scalar_one_or_none()
                        if refreshed_conn:
                            creds = self._cred_provider.retrieve_credentials(refreshed_conn)
                            if not self.is_token_expired(creds):
                                logger.info(f"Connection {conn_id_str} refreshed by concurrent worker.")
                                return creds
                    # If still expired after waiting, proceed to attempt refresh ourselves
            except Exception as e:
                logger.warning(f"Distributed lock attempt failed in Redis: {e}")

        try:
            # 2. Re-check credentials in case they were updated before lock acquisition
            current_creds = self._cred_provider.retrieve_credentials(connection)
            if not force_refresh and not self.is_token_expired(current_creds):
                return current_creds

            refresh_token = current_creds.get("refresh_token")
            if not refresh_token:
                logger.warning(f"Connection {conn_id_str} has no refresh token; marked REAUTH_REQUIRED.")
                connection.status = ConnectionStatus.REAUTH_REQUIRED.value
                connection.error_message = "No refresh token available. Re-authentication required."
                await session.commit()
                raise OAuthReauthRequiredError("No refresh token available. Please reconnect your account.")

            # 3. Determine provider
            if provider is None:
                provider_name = connection.provider
                tenant_id = connection.settings.get("tenant_id", "common") if connection.settings else "common"
                provider = get_email_oauth_provider(provider_name, tenant_id=tenant_id)

            settings = get_settings()
            if provider.provider_name == "google":
                client_id = settings.google_client_id or (connection.settings.get("client_id") if connection.settings else None)
                client_secret = settings.google_client_secret or (connection.settings.get("client_secret") if connection.settings else None)
            else:
                client_id = settings.microsoft_client_id or (connection.settings.get("client_id") if connection.settings else None)
                client_secret = settings.microsoft_client_secret or (connection.settings.get("client_secret") if connection.settings else None)

            if not client_id or not client_secret:
                raise OAuthTokenRefreshError(f"Missing OAuth client credentials for provider '{provider.provider_name}'")

            # 4. Perform actual provider refresh
            connection.status = ConnectionStatus.TOKEN_REFRESHING.value
            new_tokens = await provider.refresh_token(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
            )

            # 5. Build updated credentials preserving existing values
            now = datetime.now(timezone.utc)
            expires_in = new_tokens.get("expires_in", 3600)
            expires_at = now + timedelta(seconds=int(expires_in))

            updated_creds = {
                **current_creds,
                "access_token": new_tokens["access_token"],
                "expires_in": expires_in,
                "expires_at": expires_at.isoformat(),
                "obtained_at": now.isoformat(),
            }

            # Update refresh token if provider returned a new one
            if new_tokens.get("refresh_token"):
                updated_creds["refresh_token"] = new_tokens["refresh_token"]

            if new_tokens.get("scope"):
                updated_creds["scope"] = new_tokens["scope"]

            # 6. Securely persist via EncryptedCredentialProvider
            self._cred_provider.store_credentials(connection, updated_creds)
            connection.status = ConnectionStatus.CONNECTED.value
            connection.error_message = None
            connection.last_sync_at = now

            await session.commit()
            logger.info(f"Token refreshed and encrypted successfully for connection {conn_id_str}")
            return updated_creds

        except OAuthReauthRequiredError as e:
            connection.status = ConnectionStatus.REAUTH_REQUIRED.value
            connection.error_message = str(e)
            await session.commit()
            raise
        except (OAuthNetworkError, OAuthTokenRefreshError) as e:
            connection.status = ConnectionStatus.CONNECTION_ERROR.value
            connection.error_message = str(e)
            await session.commit()
            raise
        except Exception as e:
            connection.status = ConnectionStatus.CONNECTION_ERROR.value
            connection.error_message = f"Unexpected token refresh error: {e}"
            await session.commit()
            raise OAuthTokenRefreshError(f"Unexpected refresh error: {e}")
        finally:
            # Release distributed lock
            if redis_client and lock_acquired:
                try:
                    await redis_client.delete(lock_key)
                except Exception:
                    pass


default_token_manager = EmailTokenManager()
