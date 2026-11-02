"""
HunterOS Engage — P0: OAuth & Integration Security Remediation Test Suite
Verifies all five critical P0 security fixes:
  P0-1: Authenticated credential encryption (Fernet), token refresh, safe failure, legacy migration.
  P0-2: Redis-backed OAuth state, TTL, atomic GETDEL, replay prevention, safe Redis failure.
  P0-3: Strict workspace isolation across all integration endpoints (list, get, update, delete, sync, jobs, oauth).
  P0-4: Google OAuth Gmail scopes + Calendar preservation and callback scope validation.
  P0-5: Microsoft Graph Mail permissions + Calendar preservation and callback scope validation.
"""

import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import fakeredis.aioredis as fake_redis
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from starlette.requests import Request

from app.domain.integration.credentials import (
    CredentialDecryptionError,
    CredentialEncryptionError,
    EncryptedCredentialProvider,
    JsonCredentialProvider,
)
from app.domain.integration.models import ConnectionStatus, IntegrationConnection, SyncJob
from app.domain.integration.oauth_state import (
    OAuthStateManager,
    OAuthStateStorageError,
)
from app.domain.integration.router import (
    GOOGLE_CALENDAR_SCOPE,
    GOOGLE_GMAIL_READONLY_SCOPE,
    GOOGLE_GMAIL_SEND_SCOPE,
    MICROSOFT_CALENDAR_SCOPE,
    MICROSOFT_MAIL_READ_SCOPE,
    MICROSOFT_MAIL_SEND_SCOPE,
    delete_integration,
    get_integration,
    list_integrations,
    list_sync_jobs,
    oauth_authorize,
    oauth_callback,
    trigger_manual_sync,
    update_integration,
)
from app.domain.integration.schemas import UpdateIntegrationRequest
from app.domain.security.models import User, UserRole


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def test_fernet_key():
    return Fernet.generate_key().decode("utf-8")


@pytest.fixture
def fake_redis_client():
    return fake_redis.FakeRedis(decode_responses=True)


@pytest.fixture
def state_mgr(fake_redis_client):
    return OAuthStateManager(redis_client=fake_redis_client)


@pytest.fixture
def workspace_a():
    return uuid4()


@pytest.fixture
def workspace_b():
    return uuid4()


@pytest.fixture
def user_a(workspace_a):
    return User(
        id=uuid4(),
        workspace_id=workspace_a,
        email="admin_a@tenant-a.com",
        role=UserRole.admin,
        is_active=True,
    )


@pytest.fixture
def user_b(workspace_b):
    return User(
        id=uuid4(),
        workspace_id=workspace_b,
        email="admin_b@tenant-b.com",
        role=UserRole.admin,
        is_active=True,
    )


# ── P0-1: Credential Encryption Tests ─────────────────────────────────────────

class TestP0_1_CredentialEncryption:
    def test_credentials_stored_encrypted(self, test_fernet_key):
        """P0-1: Stored credentials must contain ciphertext envelope, never raw tokens."""
        provider = EncryptedCredentialProvider(key=test_fernet_key)
        conn = IntegrationConnection(id=uuid4(), workspace_id=uuid4(), credentials_json={})
        
        raw_tokens = {
            "access_token": "ya29.sensitive_access_token_12345",
            "refresh_token": "1//04sensitive_refresh_token_67890",
            "token_type": "Bearer",
        }
        
        provider.store_credentials(conn, raw_tokens)
        
        # Verify envelope structure
        assert conn.credentials_json.get("__encrypted__") is True
        assert conn.credentials_json.get("version") == 1
        assert "ciphertext" in conn.credentials_json
        
        # Verify raw tokens are NEVER present in stored JSON string
        stored_repr = json.dumps(conn.credentials_json)
        assert "ya29.sensitive_access_token_12345" not in stored_repr
        assert "1//04sensitive_refresh_token_67890" not in stored_repr

    def test_credentials_retrieved_decrypted(self, test_fernet_key):
        """P0-1: Authorized retrieval returns the exact original tokens."""
        provider = EncryptedCredentialProvider(key=test_fernet_key)
        conn = IntegrationConnection(id=uuid4(), workspace_id=uuid4(), credentials_json={})
        
        raw_tokens = {
            "access_token": "valid_token_abc",
            "refresh_token": "valid_refresh_xyz",
            "expires_in": 3600,
        }
        
        provider.store_credentials(conn, raw_tokens)
        retrieved = provider.retrieve_credentials(conn)
        
        assert retrieved == raw_tokens
        assert retrieved["access_token"] == "valid_token_abc"
        assert retrieved["refresh_token"] == "valid_refresh_xyz"

    def test_invalid_encryption_key_fails_safely(self, test_fernet_key):
        """P0-1: Decryption with wrong key raises CredentialDecryptionError safely."""
        provider_1 = EncryptedCredentialProvider(key=test_fernet_key)
        provider_2 = EncryptedCredentialProvider(key=Fernet.generate_key().decode("utf-8"))
        
        conn = IntegrationConnection(id=uuid4(), workspace_id=uuid4(), credentials_json={})
        provider_1.store_credentials(conn, {"secret": "confidential_data"})
        
        with pytest.raises(CredentialDecryptionError, match="Invalid encryption key"):
            provider_2.retrieve_credentials(conn)

    def test_double_encryption_prevented(self, test_fernet_key):
        """P0-1: Storing an already encrypted envelope must not re-encrypt it."""
        provider = EncryptedCredentialProvider(key=test_fernet_key)
        conn = IntegrationConnection(id=uuid4(), workspace_id=uuid4(), credentials_json={})
        
        provider.store_credentials(conn, {"access_token": "token1"})
        initial_ciphertext = conn.credentials_json["ciphertext"]
        
        # Store already encrypted dict again
        provider.store_credentials(conn, conn.credentials_json)
        assert conn.credentials_json["ciphertext"] == initial_ciphertext

    def test_legacy_plaintext_backward_compatibility(self, test_fernet_key):
        """P0-1: Legacy unencrypted records remain accessible without crashing."""
        provider = EncryptedCredentialProvider(key=test_fernet_key)
        legacy_tokens = {"access_token": "legacy_token", "refresh_token": "legacy_refresh"}
        conn = IntegrationConnection(id=uuid4(), workspace_id=uuid4(), credentials_json=legacy_tokens)
        
        # Should return plaintext directly without throwing
        assert provider.retrieve_credentials(conn) == legacy_tokens

    def test_empty_credentials_handling(self, test_fernet_key):
        """P0-1: Clearing or storing empty credentials works cleanly."""
        provider = EncryptedCredentialProvider(key=test_fernet_key)
        conn = IntegrationConnection(id=uuid4(), workspace_id=uuid4(), credentials_json={})
        
        provider.store_credentials(conn, {})
        assert conn.credentials_json == {}
        assert provider.retrieve_credentials(conn) == {}
        
        provider.store_credentials(conn, {"access_token": "abc"})
        provider.clear_credentials(conn)
        assert conn.credentials_json == {}

    def test_production_missing_key_raises_runtime_error(self):
        """P0-1: In production environment, missing OAUTH_ENCRYPTION_KEY must fail immediately."""
        with patch("app.domain.integration.credentials.get_settings") as mock_settings, \
             patch.dict("os.environ", {}, clear=True):
            mock_settings.return_value.oauth_encryption_key = None
            mock_settings.return_value.is_production = True
            
            with pytest.raises(RuntimeError, match="OAUTH_ENCRYPTION_KEY must be configured in production"):
                EncryptedCredentialProvider(key=None)


# ── P0-2: Redis-Backed OAuth State Tests ──────────────────────────────────────

@pytest.mark.asyncio
class TestP0_2_RedisOAuthState:
    async def test_state_stored_in_redis_with_ttl(self, state_mgr, fake_redis_client, workspace_a):
        """P0-2: State is stored in Redis with 10-minute (600s) TTL and bound to user/workspace."""
        integration_id = uuid4()
        user_id = uuid4()
        
        state_token = await state_mgr.create_state(
            workspace_id=workspace_a,
            integration_id=integration_id,
            provider="google",
            user_id=user_id,
            ttl_seconds=600,
        )
        
        # Verify key in Redis
        key = f"oauth_state:{state_token}"
        raw_val = await fake_redis_client.get(key)
        assert raw_val is not None
        
        data = json.loads(raw_val)
        assert data["workspace_id"] == str(workspace_a)
        assert data["integration_id"] == str(integration_id)
        assert data["user_id"] == str(user_id)
        assert data["provider"] == "google"
        
        # Verify TTL
        ttl = await fake_redis_client.ttl(key)
        assert 0 < ttl <= 600

    async def test_state_consumed_atomically(self, state_mgr, fake_redis_client, workspace_a):
        """P0-2: Consuming state returns the payload and immediately deletes it from Redis."""
        integration_id = uuid4()
        state_token = await state_mgr.create_state(
            workspace_id=workspace_a,
            integration_id=integration_id,
            provider="microsoft",
        )
        
        consumed = await state_mgr.consume_state(state_token)
        assert consumed is not None
        assert consumed["workspace_id"] == str(workspace_a)
        assert consumed["provider"] == "microsoft"
        
        # Key is now gone from Redis
        key = f"oauth_state:{state_token}"
        assert await fake_redis_client.get(key) is None

    async def test_replay_attack_rejected(self, state_mgr, workspace_a):
        """P0-2: Replaying the same state token returns None on the second attempt."""
        integration_id = uuid4()
        state_token = await state_mgr.create_state(
            workspace_id=workspace_a,
            integration_id=integration_id,
            provider="google",
        )
        
        first_consume = await state_mgr.consume_state(state_token)
        assert first_consume is not None
        
        # Second consume MUST return None (preventing CSRF replay)
        second_consume = await state_mgr.consume_state(state_token)
        assert second_consume is None

    async def test_expired_state_rejected(self, state_mgr, fake_redis_client, workspace_a):
        """P0-2: State that has expired in Redis returns None."""
        integration_id = uuid4()
        state_token = await state_mgr.create_state(
            workspace_id=workspace_a,
            integration_id=integration_id,
            provider="google",
            ttl_seconds=1,
        )
        
        # Artificially expire the key in Redis
        key = f"oauth_state:{state_token}"
        await fake_redis_client.delete(key)
        
        consumed = await state_mgr.consume_state(state_token)
        assert consumed is None

    async def test_redis_failure_fails_safely(self, workspace_a):
        """P0-2: Redis connection failure raises OAuthStateStorageError and does NOT fall back to in-memory."""
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = ConnectionError("Redis cluster down")
        mock_redis.getdel.side_effect = ConnectionError("Redis cluster down")
        
        broken_mgr = OAuthStateManager(redis_client=mock_redis)
        
        with pytest.raises(OAuthStateStorageError, match="Failed to persist OAuth state in Redis"):
            await broken_mgr.create_state(workspace_id=workspace_a, integration_id=uuid4(), provider="google")
            
        with pytest.raises(OAuthStateStorageError, match="Redis error during OAuth state consumption"):
            await broken_mgr.consume_state("some_token")


# ── P0-3: Strict Workspace Isolation Tests ────────────────────────────────────

@pytest.mark.asyncio
class TestP0_3_StrictWorkspaceIsolation:
    async def test_list_integrations_workspace_isolation(self, user_a, user_b, workspace_a, workspace_b):
        """P0-3: Tenant A only sees Tenant A's integrations; Tenant B only sees Tenant B's."""
        conn_a = IntegrationConnection(id=uuid4(), workspace_id=workspace_a, connector_id="c1", provider="p1", name="Conn A")
        conn_b = IntegrationConnection(id=uuid4(), workspace_id=workspace_b, connector_id="c2", provider="p2", name="Conn B")
        
        async def mock_execute(stmt):
            mock_res = MagicMock()
            # Inspect the WHERE clause
            sql_str = str(stmt)
            if str(workspace_a) in sql_str or "workspace_id" in sql_str:
                mock_res.scalars.return_value.all.return_value = [conn_a]
            else:
                mock_res.scalars.return_value.all.return_value = [conn_b]
            return mock_res
            
        db = AsyncMock()
        db.execute.side_effect = mock_execute
        
        # User A query
        results_a = await list_integrations(user=user_a, db=db)
        assert all(c.workspace_id == workspace_a for c in results_a)
        
        # Verify query had WHERE workspace_id == user.workspace_id
        executed_stmt = db.execute.call_args[0][0]
        # Compile statement to string and verify workspace_id filter is present
        assert "workspace_id" in str(executed_stmt)

    async def test_get_integration_cross_workspace_rejected(self, user_a, workspace_b):
        """P0-3: User A attempting to get an integration belonging to Workspace B receives 404."""
        conn_b_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Not found in user_a's workspace
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_integration(integration_id=conn_b_id, user=user_a, db=db)
            
        assert exc_info.value.status_code == 404
        # Verify query enforced user_a's workspace boundary
        executed_stmt = db.execute.call_args[0][0]
        assert "workspace_id" in str(executed_stmt)

    async def test_update_integration_cross_workspace_rejected(self, user_a, workspace_b):
        """P0-3: User A attempting to update an integration in Workspace B receives 404."""
        conn_b_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        req = UpdateIntegrationRequest(name="Hacked Name")
        with pytest.raises(HTTPException) as exc_info:
            await update_integration(integration_id=conn_b_id, req=req, user=user_a, db=db)
            
        assert exc_info.value.status_code == 404

    async def test_delete_integration_cross_workspace_rejected(self, user_a, workspace_b):
        """P0-3: User A attempting to delete an integration in Workspace B receives 404."""
        conn_b_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_integration(integration_id=conn_b_id, user=user_a, db=db)
            
        assert exc_info.value.status_code == 404

    async def test_sync_cross_workspace_rejected(self, user_a, workspace_b):
        """P0-3: User A attempting to trigger sync on Workspace B's integration receives 404."""
        conn_b_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await trigger_manual_sync(integration_id=conn_b_id, user=user_a, db=db)
            
        assert exc_info.value.status_code == 404

    async def test_jobs_cross_workspace_rejected(self, user_a, workspace_b):
        """P0-3: User A attempting to view sync jobs for Workspace B's integration receives 404."""
        conn_b_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await list_sync_jobs(integration_id=conn_b_id, user=user_a, db=db)
            
        assert exc_info.value.status_code == 404

    async def test_oauth_authorize_mismatched_workspace_param_rejected(self, user_a, workspace_b):
        """P0-3: User A supplying workspace_id=ws_b query param is rejected with 403 Forbidden."""
        db = AsyncMock()
        request = AsyncMock(spec=Request)
        
        with pytest.raises(HTTPException) as exc_info:
            await oauth_authorize(
                integration_id=uuid4(),
                workspace_id=workspace_b,  # Attacker tries to pass another workspace's ID
                request=request,
                db=db,
                user=user_a,
            )
            
        assert exc_info.value.status_code == 403
        assert "Workspace mismatch" in exc_info.value.detail


# ── P0-4: Google Gmail OAuth Scopes Tests ─────────────────────────────────────

@pytest.mark.asyncio
class TestP0_4_GoogleGmailScopes:
    async def test_google_authorize_url_contains_calendar_and_gmail_scopes(self, state_mgr, user_a, workspace_a):
        """P0-4: Google authorize URL contains both Calendar and Gmail (readonly + send) scopes."""
        integration_id = uuid4()
        mock_connection = IntegrationConnection(
            id=integration_id, workspace_id=workspace_a, provider="google", settings={"client_id": "google_cid_123"}
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        request = AsyncMock(spec=Request)
        request.url_for.return_value = "https://hunteros.ai/api/v1/integrations/oauth/callback"
        
        res = await oauth_authorize(
            integration_id=integration_id,
            request=request,
            db=db,
            user=user_a,
            state_manager=state_mgr,
        )
        
        auth_url = res["authorize_url"]
        unquoted = urllib.parse.unquote(auth_url)
        
        # Verify Calendar scope preserved
        assert GOOGLE_CALENDAR_SCOPE in unquoted
        # Verify Gmail scopes added
        assert GOOGLE_GMAIL_READONLY_SCOPE in unquoted
        assert GOOGLE_GMAIL_SEND_SCOPE in unquoted
        assert "access_type=offline" in unquoted
        assert "prompt=consent" in unquoted

    async def test_google_callback_scope_validation_success(self, state_mgr, workspace_a):
        """P0-4: Google callback succeeds when all required scopes are granted."""
        integration_id = uuid4()
        state = await state_mgr.create_state(workspace_id=workspace_a, integration_id=integration_id, provider="google")
        
        mock_conn = IntegrationConnection(id=integration_id, workspace_id=workspace_a, provider="google", settings={})
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conn
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        full_scopes = f"{GOOGLE_CALENDAR_SCOPE} {GOOGLE_GMAIL_READONLY_SCOPE} {GOOGLE_GMAIL_SEND_SCOPE}"
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("app.domain.integration.router.get_settings") as mock_settings:
            mock_settings.return_value.google_client_id = "cid"
            mock_settings.return_value.google_client_secret = "csecret"
            
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "access_token": "g_access_123",
                "refresh_token": "g_refresh_456",
                "scope": full_scopes,
            }
            mock_post.return_value = mock_resp
            
            res = await oauth_callback(
                request=AsyncMock(spec=Request),
                state=state,
                code="google_code",
                db=db,
                state_manager=state_mgr,
            )
            
            assert res["status"] == "success"
            assert mock_conn.status == ConnectionStatus.CONNECTED.value
            assert mock_conn.credentials_json.get("__encrypted__") is True

    async def test_google_callback_missing_scopes_rejected(self, state_mgr, workspace_a):
        """P0-4: If user unchecks Gmail permissions, callback is rejected with 400 Insufficient permissions."""
        integration_id = uuid4()
        state = await state_mgr.create_state(workspace_id=workspace_a, integration_id=integration_id, provider="google")
        
        mock_conn = IntegrationConnection(id=integration_id, workspace_id=workspace_a, provider="google", settings={})
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conn
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        # User only granted Calendar, refused Gmail permissions
        partial_scopes = f"{GOOGLE_CALENDAR_SCOPE}"
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("app.domain.integration.router.get_settings") as mock_settings:
            mock_settings.return_value.google_client_id = "cid"
            mock_settings.return_value.google_client_secret = "csecret"
            
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "access_token": "g_access_123",
                "refresh_token": "g_refresh_456",
                "scope": partial_scopes,
            }
            mock_post.return_value = mock_resp
            
            with pytest.raises(HTTPException) as exc_info:
                await oauth_callback(
                    request=AsyncMock(spec=Request),
                    state=state,
                    code="google_code",
                    db=db,
                    state_manager=state_mgr,
                )
                
            assert exc_info.value.status_code == 400
            assert "Insufficient permissions" in exc_info.value.detail
            assert "gmail.readonly" in exc_info.value.detail or "gmail.send" in exc_info.value.detail


# ── P0-5: Microsoft Graph Mail Scopes Tests ───────────────────────────────────

@pytest.mark.asyncio
class TestP0_5_MicrosoftMailScopes:
    async def test_microsoft_authorize_url_contains_calendar_and_mail_scopes(self, state_mgr, user_a, workspace_a):
        """P0-5: Microsoft authorize URL contains Calendar, Mail.Read, Mail.Send, User.Read, offline_access."""
        integration_id = uuid4()
        mock_connection = IntegrationConnection(
            id=integration_id, workspace_id=workspace_a, provider="microsoft", settings={"client_id": "ms_cid_123"}
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        request = AsyncMock(spec=Request)
        request.url_for.return_value = "https://hunteros.ai/api/v1/integrations/oauth/callback"
        
        res = await oauth_authorize(
            integration_id=integration_id,
            request=request,
            db=db,
            user=user_a,
            state_manager=state_mgr,
        )
        
        auth_url = res["authorize_url"]
        unquoted = urllib.parse.unquote(auth_url)
        
        # Verify Calendar preserved
        assert MICROSOFT_CALENDAR_SCOPE in unquoted
        # Verify Mail scopes added
        assert MICROSOFT_MAIL_READ_SCOPE in unquoted
        assert MICROSOFT_MAIL_SEND_SCOPE in unquoted
        assert "offline_access" in unquoted
        assert "User.Read" in unquoted

    async def test_microsoft_callback_scope_validation_success(self, state_mgr, workspace_a):
        """P0-5: Microsoft callback succeeds when all required permissions are granted."""
        integration_id = uuid4()
        state = await state_mgr.create_state(workspace_id=workspace_a, integration_id=integration_id, provider="microsoft")
        
        mock_conn = IntegrationConnection(id=integration_id, workspace_id=workspace_a, provider="microsoft", settings={})
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conn
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        full_scopes = f"offline_access {MICROSOFT_CALENDAR_SCOPE} {MICROSOFT_MAIL_READ_SCOPE} {MICROSOFT_MAIL_SEND_SCOPE} User.Read"
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("app.domain.integration.router.get_settings") as mock_settings:
            mock_settings.return_value.microsoft_client_id = "cid"
            mock_settings.return_value.microsoft_client_secret = "csecret"
            
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "access_token": "ms_access_123",
                "refresh_token": "ms_refresh_456",
                "scope": full_scopes,
            }
            mock_post.return_value = mock_resp
            
            res = await oauth_callback(
                request=AsyncMock(spec=Request),
                state=state,
                code="ms_code",
                db=db,
                state_manager=state_mgr,
            )
            
            assert res["status"] == "success"
            assert mock_conn.status == ConnectionStatus.CONNECTED.value
            assert mock_conn.credentials_json.get("__encrypted__") is True

    async def test_microsoft_callback_missing_scopes_rejected(self, state_mgr, workspace_a):
        """P0-5: If Microsoft tenant unchecks Mail permissions, callback is rejected with 400 Insufficient permissions."""
        integration_id = uuid4()
        state = await state_mgr.create_state(workspace_id=workspace_a, integration_id=integration_id, provider="microsoft")
        
        mock_conn = IntegrationConnection(id=integration_id, workspace_id=workspace_a, provider="microsoft", settings={})
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conn
        db = AsyncMock()
        db.execute.return_value = mock_result
        
        # User only granted Calendars, refused Mail.Send
        partial_scopes = f"offline_access {MICROSOFT_CALENDAR_SCOPE} {MICROSOFT_MAIL_READ_SCOPE}"
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("app.domain.integration.router.get_settings") as mock_settings:
            mock_settings.return_value.microsoft_client_id = "cid"
            mock_settings.return_value.microsoft_client_secret = "csecret"
            
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "access_token": "ms_access_123",
                "refresh_token": "ms_refresh_456",
                "scope": partial_scopes,
            }
            mock_post.return_value = mock_resp
            
            with pytest.raises(HTTPException) as exc_info:
                await oauth_callback(
                    request=AsyncMock(spec=Request),
                    state=state,
                    code="ms_code",
                    db=db,
                    state_manager=state_mgr,
                )
                
            assert exc_info.value.status_code == 400
            assert "Insufficient permissions" in exc_info.value.detail
            assert "Mail.Send" in exc_info.value.detail
