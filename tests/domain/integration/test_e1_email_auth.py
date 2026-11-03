"""
HunterOS Engage — Milestone E1: Email Provider Authentication Test Suite

Comprehensive tests for:
  - Google Gmail OAuth Provider (URL generation, code exchange, scope validation, identity extraction, refresh, connectivity)
  - Microsoft Graph OAuth Provider (URL generation, code exchange, scope validation, identity extraction, refresh, connectivity)
  - Token Lifecycle Management (EmailTokenManager, distributed lock, expiration buffer, reauth transitions, credential persistence)
  - Production Connectors (GmailEmailConnector, OutlookEmailConnector, auto-refresh on health check)
  - Connection Management Endpoints (/email/authorize, /email/status, /{id}/health-check, /{id}/refresh, /{id}/disconnect)
  - Multi-tenant workspace isolation and credential confidentiality (no token leakage)
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

from app.domain.integration.bootstrap import bootstrap_integrations
from app.domain.integration.connectors.gmail import GmailEmailConnector
from app.domain.integration.connectors.outlook_mail import OutlookEmailConnector
from app.domain.integration.connectors.registry import connector_registry
from app.domain.integration.credentials import EncryptedCredentialProvider
from app.domain.integration.email_auth.manager import EmailTokenManager
from app.domain.integration.email_auth.provider import (
    GoogleGmailOAuthProvider,
    MicrosoftGraphOAuthProvider,
    OAuthCodeExchangeError,
    OAuthIdentityError,
    OAuthNetworkError,
    OAuthReauthRequiredError,
    OAuthScopeError,
    OAuthTokenRefreshError,
    get_email_oauth_provider,
)
from app.domain.integration.models import ConnectionStatus, IntegrationConnection
from app.domain.integration.oauth_state import OAuthStateManager
from app.domain.integration.router import (
    GOOGLE_CALENDAR_SCOPE,
    GOOGLE_GMAIL_READONLY_SCOPE,
    GOOGLE_GMAIL_SEND_SCOPE,
    MICROSOFT_CALENDAR_SCOPE,
    MICROSOFT_MAIL_READ_SCOPE,
    MICROSOFT_MAIL_SEND_SCOPE,
    check_integration_health,
    disconnect_integration,
    email_authorize,
    list_email_integrations_status,
    oauth_callback,
    refresh_integration_token,
)
from app.domain.security.models import User, UserRole


# ── Shared Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def test_fernet_key(monkeypatch):
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("OAUTH_ENCRYPTION_KEY", key)
    from app.config import get_settings
    get_settings.cache_clear()
    yield key
    get_settings.cache_clear()


@pytest.fixture
def fake_redis_client():
    return fake_redis.FakeRedis(decode_responses=True)


@pytest.fixture
def state_mgr(fake_redis_client):
    return OAuthStateManager(redis_client=fake_redis_client)


@pytest.fixture
def cred_provider(test_fernet_key):
    return EncryptedCredentialProvider(key=test_fernet_key)


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
        email="owner@tenant-alpha.com",
        role=UserRole.admin,
        is_active=True,
    )


@pytest.fixture
def user_b(workspace_b):
    return User(
        id=uuid4(),
        workspace_id=workspace_b,
        email="owner@tenant-beta.com",
        role=UserRole.admin,
        is_active=True,
    )


# ── 1. Google Gmail Provider Tests ────────────────────────────────────────────

class TestGoogleGmailOAuthProvider:
    def test_provider_metadata_and_scopes(self):
        provider = GoogleGmailOAuthProvider()
        assert provider.provider_name == "google"
        assert GOOGLE_CALENDAR_SCOPE in provider.required_scopes
        assert GOOGLE_GMAIL_READONLY_SCOPE in provider.required_scopes
        assert GOOGLE_GMAIL_SEND_SCOPE in provider.required_scopes

    def test_get_authorization_url_contains_all_scopes(self):
        provider = GoogleGmailOAuthProvider()
        url = provider.get_authorization_url(
            client_id="g_client_123",
            redirect_uri="https://api.hunteros.ai/callback",
            state_token="secure_state_xyz",
        )
        unquoted = urllib.parse.unquote(url)
        assert "accounts.google.com/o/oauth2/v2/auth" in url
        assert "client_id=g_client_123" in url
        assert "state=secure_state_xyz" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url
        assert GOOGLE_CALENDAR_SCOPE in unquoted
        assert GOOGLE_GMAIL_READONLY_SCOPE in unquoted
        assert GOOGLE_GMAIL_SEND_SCOPE in unquoted

    def test_scope_validation_success_and_failure(self):
        provider = GoogleGmailOAuthProvider()
        full_scope = f"{GOOGLE_CALENDAR_SCOPE} {GOOGLE_GMAIL_READONLY_SCOPE} {GOOGLE_GMAIL_SEND_SCOPE}"
        valid, missing = provider.validate_scopes(full_scope)
        assert valid is True
        assert len(missing) == 0

        partial_scope = f"{GOOGLE_CALENDAR_SCOPE}"
        valid, missing = provider.validate_scopes(partial_scope)
        assert valid is False
        assert GOOGLE_GMAIL_READONLY_SCOPE in missing
        assert GOOGLE_GMAIL_SEND_SCOPE in missing

    @pytest.mark.asyncio
    async def test_code_exchange_success(self):
        provider = GoogleGmailOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "g_access_token",
            "refresh_token": "g_refresh_token",
            "expires_in": 3599,
            "scope": f"{GOOGLE_GMAIL_READONLY_SCOPE} {GOOGLE_GMAIL_SEND_SCOPE}",
            "token_type": "Bearer",
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            tokens = await provider.exchange_code("cid", "csecret", "valid_code", "https://redirect")
            assert tokens["access_token"] == "g_access_token"
            assert tokens["refresh_token"] == "g_refresh_token"

    @pytest.mark.asyncio
    async def test_code_exchange_error_handling(self):
        provider = GoogleGmailOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"error": "invalid_grant", "error_description": "Code expired"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            with pytest.raises(OAuthCodeExchangeError, match="Code expired"):
                await provider.exchange_code("cid", "csecret", "bad_code", "https://redirect")

    @pytest.mark.asyncio
    async def test_token_refresh_preserves_original_refresh_token(self):
        provider = GoogleGmailOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Google does not return a new refresh token on refresh
        mock_resp.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            tokens = await provider.refresh_token("cid", "csecret", "original_refresh_token")
            assert tokens["access_token"] == "new_access_token"
            assert tokens["refresh_token"] == "original_refresh_token"

    @pytest.mark.asyncio
    async def test_token_refresh_revoked_raises_reauth_required(self):
        provider = GoogleGmailOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"error": "invalid_grant", "error_description": "Token has been revoked"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            with pytest.raises(OAuthReauthRequiredError, match="revoked"):
                await provider.refresh_token("cid", "csecret", "revoked_token")

    @pytest.mark.asyncio
    async def test_get_account_identity_success(self):
        provider = GoogleGmailOAuthProvider()
        profile_resp = MagicMock()
        profile_resp.status_code = 200
        profile_resp.json.return_value = {
            "emailAddress": "alex@company.com",
            "messagesTotal": 4200,
            "historyId": "987654",
        }

        userinfo_resp = MagicMock()
        userinfo_resp.status_code = 200
        userinfo_resp.json.return_value = {
            "id": "google_sub_12345",
            "email": "alex@company.com",
            "name": "Alex Mercer",
        }

        async def mock_get(url, **kwargs):
            if "profile" in url:
                return profile_resp
            return userinfo_resp

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            identity = await provider.get_account_identity("valid_token")
            assert identity["email"] == "alex@company.com"
            assert identity["display_name"] == "Alex Mercer"
            assert identity["provider_account_id"] == "google_sub_12345"
            assert identity["metadata"]["messages_total"] == 4200

    @pytest.mark.asyncio
    async def test_check_connectivity_success_and_failure(self):
        provider = GoogleGmailOAuthProvider()
        mock_ok = MagicMock(status_code=200)
        mock_err = MagicMock(status_code=401, text="Invalid Credentials")

        with patch("httpx.AsyncClient.get", return_value=mock_ok):
            connected, err = await provider.check_connectivity("valid_token")
            assert connected is True
            assert err is None

        with patch("httpx.AsyncClient.get", return_value=mock_err):
            connected, err = await provider.check_connectivity("bad_token")
            assert connected is False
            assert "401" in err


# ── 2. Microsoft Graph Provider Tests ─────────────────────────────────────────

class TestMicrosoftGraphOAuthProvider:
    def test_provider_metadata_and_scopes(self):
        provider = MicrosoftGraphOAuthProvider(tenant_id="common")
        assert provider.provider_name == "microsoft"
        assert MICROSOFT_CALENDAR_SCOPE in provider.required_scopes
        assert MICROSOFT_MAIL_READ_SCOPE in provider.required_scopes
        assert MICROSOFT_MAIL_SEND_SCOPE in provider.required_scopes

    def test_get_authorization_url_structure(self):
        provider = MicrosoftGraphOAuthProvider(tenant_id="organizations")
        url = provider.get_authorization_url(
            client_id="ms_client_guid",
            redirect_uri="https://api.hunteros.ai/callback",
            state_token="state_ms_456",
        )
        unquoted = urllib.parse.unquote(url)
        assert "login.microsoftonline.com/organizations/oauth2/v2.0/authorize" in url
        assert "client_id=ms_client_guid" in url
        assert "state=state_ms_456" in url
        assert MICROSOFT_MAIL_READ_SCOPE in unquoted
        assert MICROSOFT_MAIL_SEND_SCOPE in unquoted
        assert MICROSOFT_CALENDAR_SCOPE in unquoted

    def test_scope_validation_success_and_failure(self):
        provider = MicrosoftGraphOAuthProvider()
        full_scope = f"{MICROSOFT_CALENDAR_SCOPE} {MICROSOFT_MAIL_READ_SCOPE} {MICROSOFT_MAIL_SEND_SCOPE} User.Read"
        valid, missing = provider.validate_scopes(full_scope)
        assert valid is True
        assert len(missing) == 0

        partial_scope = "User.Read Calendars.ReadWrite"
        valid, missing = provider.validate_scopes(partial_scope)
        assert valid is False
        assert MICROSOFT_MAIL_READ_SCOPE in missing
        assert MICROSOFT_MAIL_SEND_SCOPE in missing

    @pytest.mark.asyncio
    async def test_get_account_identity_success_with_mail(self):
        provider = MicrosoftGraphOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "ms_user_id_999",
            "displayName": "Sarah Connor",
            "mail": "sarah@cyberdyne.org",
            "userPrincipalName": "sarah@cyberdyne.onmicrosoft.com",
            "jobTitle": "Lead Engineer",
        }

        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            identity = await provider.get_account_identity("valid_ms_token")
            assert identity["email"] == "sarah@cyberdyne.org"
            assert identity["display_name"] == "Sarah Connor"
            assert identity["provider_account_id"] == "ms_user_id_999"

    @pytest.mark.asyncio
    async def test_get_account_identity_fallback_to_user_principal_name(self):
        provider = MicrosoftGraphOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "ms_user_id_888",
            "displayName": "John Connor",
            "mail": None,  # Personal accounts may omit mail
            "userPrincipalName": "john@outlook.com",
        }

        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            identity = await provider.get_account_identity("valid_ms_token")
            assert identity["email"] == "john@outlook.com"
            assert identity["display_name"] == "John Connor"

    @pytest.mark.asyncio
    async def test_token_refresh_revocation_error(self):
        provider = MicrosoftGraphOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {
            "error": "invalid_grant",
            "error_description": "AADSTS700082: The refresh token has expired due to inactivity.",
        }

        with patch("httpx.AsyncClient.post", return_value=mock_resp):
            with pytest.raises(OAuthReauthRequiredError, match="expired due to inactivity"):
                await provider.refresh_token("cid", "csecret", "expired_token")

    @pytest.mark.asyncio
    async def test_check_connectivity_inbox_and_fallback(self):
        provider = MicrosoftGraphOAuthProvider()
        mock_ok = MagicMock(status_code=200)
        with patch("httpx.AsyncClient.get", return_value=mock_ok):
            connected, err = await provider.check_connectivity("valid_ms_token")
            assert connected is True
            assert err is None

        # Inbox 403, /me 200 fallback
        inbox_denied = MagicMock(status_code=403, text="Forbidden")
        me_ok = MagicMock(status_code=200)

        async def mock_get(url, **kwargs):
            if "mailFolders" in url:
                return inbox_denied
            return me_ok

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            connected, err = await provider.check_connectivity("valid_token")
            assert connected is True


# ── 3. Token Lifecycle & EmailTokenManager Tests ──────────────────────────────

@pytest.mark.asyncio
class TestEmailTokenManager:
    async def test_is_token_expired_with_buffer(self, cred_provider):
        token_mgr = EmailTokenManager(db=AsyncMock(), cred_provider=cred_provider)

        # Expired in past
        now_ts = datetime.now(timezone.utc).timestamp()
        expired_creds = {"expires_at": now_ts - 100}
        assert token_mgr.is_token_expired(expired_creds) is True

        # Within 300s buffer -> treated as expired for proactive refresh
        expiring_soon_creds = {"expires_at": now_ts + 200}
        assert token_mgr.is_token_expired(expiring_soon_creds, buffer_seconds=300) is True

        # Valid beyond buffer
        valid_creds = {"expires_at": now_ts + 1200}
        assert token_mgr.is_token_expired(valid_creds, buffer_seconds=300) is False

    async def test_refresh_token_acquires_lock_and_persists_credentials(
        self, cred_provider, fake_redis_client, workspace_a
    ):
        db = AsyncMock()
        conn_id = uuid4()
        conn = IntegrationConnection(
            id=conn_id,
            workspace_id=workspace_a,
            provider="google",
            connector_id="google_gmail_v1",
            status=ConnectionStatus.CONNECTED.value,
            credentials_json={},
            settings={"client_id": "cid", "client_secret": "csecret"},
        )
        cred_provider.store_credentials(conn, {
            "access_token": "old_access",
            "refresh_token": "test_refresh",
            "expires_at": datetime.now(timezone.utc).timestamp() - 50,
        })

        token_mgr = EmailTokenManager(
            db=db,
            cred_provider=cred_provider,
            redis_client=fake_redis_client,
        )

        with patch.object(
            GoogleGmailOAuthProvider,
            "refresh_token",
            new_callable=AsyncMock,
            return_value={
                "access_token": "new_access_token_xyz",
                "refresh_token": "test_refresh",
                "expires_in": 3600,
            },
        ):
            updated_creds = await token_mgr.refresh_token(conn)
            assert updated_creds["access_token"] == "new_access_token_xyz"
            assert conn.status == ConnectionStatus.CONNECTED.value

            # Credentials stored in conn are encrypted
            decrypted = cred_provider.retrieve_credentials(conn)
            assert decrypted["access_token"] == "new_access_token_xyz"

            # DB commit was called
            db.commit.assert_awaited()

            # Lock should be released
            lock_key = f"lock:email_token_refresh:{conn_id}"
            assert await fake_redis_client.get(lock_key) is None

    async def test_refresh_token_revoked_transitions_to_reauth_required(
        self, cred_provider, fake_redis_client, workspace_a
    ):
        db = AsyncMock()
        conn_id = uuid4()
        conn = IntegrationConnection(
            id=conn_id,
            workspace_id=workspace_a,
            provider="google",
            connector_id="google_gmail_v1",
            status=ConnectionStatus.CONNECTED.value,
            credentials_json={},
            settings={"client_id": "cid", "client_secret": "csecret"},
        )
        cred_provider.store_credentials(conn, {
            "access_token": "old_access",
            "refresh_token": "revoked_token",
        })

        token_mgr = EmailTokenManager(
            db=db,
            cred_provider=cred_provider,
            redis_client=fake_redis_client,
        )

        with patch.object(
            GoogleGmailOAuthProvider,
            "refresh_token",
            side_effect=OAuthReauthRequiredError("Revoked by user"),
        ):
            with pytest.raises(OAuthReauthRequiredError):
                await token_mgr.refresh_token(conn)

            # Connection status in DB transitioned to REAUTH_REQUIRED
            assert conn.status == ConnectionStatus.REAUTH_REQUIRED.value
            assert "Revoked by user" in conn.error_message
            db.commit.assert_awaited()


# ── 4. Connector Registry & Connector Execution Tests ─────────────────────────

@pytest.mark.asyncio
class TestEmailConnectors:
    async def test_connectors_registered_in_bootstrap(self):
        bootstrap_integrations()
        gmail_conn = connector_registry.get_connector("google_gmail_v1")
        outlook_conn = connector_registry.get_connector("outlook_mail_v1")
        assert gmail_conn is not None
        assert isinstance(gmail_conn, GmailEmailConnector)
        assert outlook_conn is not None
        assert isinstance(outlook_conn, OutlookEmailConnector)

        # Lookup by provider helper
        assert connector_registry.get_connector_for_provider("google") is gmail_conn
        assert connector_registry.get_connector_for_provider("microsoft") is outlook_conn

    async def test_gmail_connector_health_check_auto_refresh_on_401(self):
        connector = GmailEmailConnector()
        creds = {
            "access_token": "stale_token",
            "refresh_token": "good_refresh",
        }
        settings = {"client_id": "cid", "client_secret": "csec"}

        call_count = 0

        async def mock_check(token):
            nonlocal call_count
            call_count += 1
            if token == "stale_token":
                return False, "Gmail API authentication failed (401)"
            return True, None

        with patch.object(GoogleGmailOAuthProvider, "check_connectivity", side_effect=mock_check), \
             patch.object(
                 GoogleGmailOAuthProvider,
                 "refresh_token",
                 return_value={"access_token": "fresh_token", "refresh_token": "good_refresh"},
             ):
            status_val, err = await connector.health_check(creds, settings)
            assert status_val == ConnectionStatus.CONNECTED.value
            assert err is None
            assert call_count == 2

    async def test_gmail_connector_execute_action_identity(self):
        connector = GmailEmailConnector()
        with patch.object(
            GoogleGmailOAuthProvider,
            "get_account_identity",
            return_value={"email": "inbox@gmail.com", "display_name": "Inbox User"},
        ):
            res = await connector.execute_action(
                action_name="get_account_identity",
                payload={},
                credentials={"access_token": "tok123"},
            )
            assert res["status"] == "success"
            assert res["identity"]["email"] == "inbox@gmail.com"

    async def test_outlook_connector_health_check_success(self):
        connector = OutlookEmailConnector()
        with patch.object(MicrosoftGraphOAuthProvider, "check_connectivity", return_value=(True, None)):
            status_val, err = await connector.health_check({"access_token": "ms_tok"}, {})
            assert status_val == ConnectionStatus.CONNECTED.value
            assert err is None


# ── 5. Connection Management API & Router Tests ───────────────────────────────

@pytest.mark.asyncio
class TestEmailRouterEndpoints:
    async def test_email_authorize_google_creates_pending_and_returns_url(
        self, user_a, workspace_a, state_mgr
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing pending conn

        db = AsyncMock()
        db.execute.return_value = mock_result

        request = AsyncMock(spec=Request)
        request.url_for.return_value = "https://hunteros.ai/api/v1/integrations/oauth/callback"

        with patch("app.domain.integration.router.get_settings") as mock_settings:
            mock_settings.return_value.google_client_id = "test_google_client_id"
            mock_settings.return_value.google_redirect_uri = "https://hunteros.ai/callback"
            mock_settings.return_value.microsoft_tenant_id = "common"

            resp = await email_authorize(
                provider="google",
                request=request,
                user=user_a,
                db=db,
                state_manager=state_mgr,
            )

            assert resp.provider == "google"
            assert "accounts.google.com/o/oauth2/v2/auth" in resp.authorize_url
            assert "client_id=test_google_client_id" in resp.authorize_url
            assert resp.state is not None
            db.add.assert_called_once()
            db.commit.assert_awaited()

    async def test_email_authorize_unsupported_provider_rejected(self, user_a, state_mgr):
        db = AsyncMock()
        request = AsyncMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await email_authorize(
                provider="yahoo",
                request=request,
                user=user_a,
                db=db,
                state_manager=state_mgr,
            )
        assert exc_info.value.status_code == 400
        assert "Unsupported email provider" in exc_info.value.detail

    async def test_list_email_integrations_status_confidentiality(self, user_a, workspace_a):
        """Must list workspace email integrations without leaking credentials or tokens."""
        conn1 = IntegrationConnection(
            id=uuid4(),
            workspace_id=workspace_a,
            connector_id="google_gmail_v1",
            connector_type="email",
            provider="google",
            name="Google Gmail (team@originyx.com)",
            status=ConnectionStatus.CONNECTED.value,
            credentials_json={"__encrypted__": True, "ciphertext": "SUPER_SECRET_CIPHERTEXT"},
            settings={"email": "team@originyx.com", "display_name": "Originyx Team"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [conn1]
        db = AsyncMock()
        db.execute.return_value = mock_result

        results = await list_email_integrations_status(user=user_a, db=db)
        assert len(results) == 1
        item = results[0]
        assert item.email == "team@originyx.com"
        assert item.provider == "google"
        assert item.status == ConnectionStatus.CONNECTED.value

        # Serialization to dict verifies NO credentials field is present
        data = item.model_dump()
        assert "credentials" not in data
        assert "credentials_json" not in data
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert "ciphertext" not in str(data)

    async def test_health_check_cross_workspace_rejected(self, user_a, workspace_b):
        """Cross-workspace health check is rejected with 404."""
        conn_b_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await check_integration_health(integration_id=conn_b_id, user=user_a, db=db)
        assert exc_info.value.status_code == 404

    async def test_health_check_execution_success(self, user_a, workspace_a, cred_provider):
        conn_id = uuid4()
        conn = IntegrationConnection(
            id=conn_id,
            workspace_id=workspace_a,
            connector_id="google_gmail_v1",
            provider="google",
            status=ConnectionStatus.CONNECTED.value,
            credentials_json={},
            settings={},
        )
        cred_provider.store_credentials(conn, {"access_token": "valid_token"})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        db = AsyncMock()
        db.execute.return_value = mock_result

        with patch.object(GmailEmailConnector, "health_check", return_value=(ConnectionStatus.CONNECTED.value, None)):
            res = await check_integration_health(integration_id=conn_id, user=user_a, db=db)
            assert res["healthy"] is True
            assert res["status"] == ConnectionStatus.CONNECTED.value
            db.commit.assert_awaited()

    async def test_refresh_integration_token_endpoint(self, user_a, workspace_a, cred_provider):
        conn_id = uuid4()
        conn = IntegrationConnection(
            id=conn_id,
            workspace_id=workspace_a,
            connector_id="google_gmail_v1",
            provider="google",
            status=ConnectionStatus.CONNECTED.value,
            credentials_json={},
            settings={},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        db = AsyncMock()
        db.execute.return_value = mock_result

        with patch.object(
            EmailTokenManager,
            "refresh_token",
            new_callable=AsyncMock,
            return_value={"access_token": "refreshed_tok", "refresh_token": "refr"},
        ):
            res = await refresh_integration_token(integration_id=conn_id, user=user_a, db=db)
            assert res["status"] == "success"
            assert res["connection_status"] == ConnectionStatus.CONNECTED.value

    async def test_disconnect_integration_endpoint(self, user_a, workspace_a, cred_provider):
        conn_id = uuid4()
        conn = IntegrationConnection(
            id=conn_id,
            workspace_id=workspace_a,
            connector_id="google_gmail_v1",
            provider="google",
            status=ConnectionStatus.CONNECTED.value,
            credentials_json={"access_token": "secret"},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        db = AsyncMock()
        db.execute.return_value = mock_result

        res = await disconnect_integration(integration_id=conn_id, user=user_a, db=db)
        assert res["status"] == "success"
        assert conn.status == ConnectionStatus.DISCONNECTED.value
        assert conn.credentials_json == {}
        db.commit.assert_awaited()

    async def test_oauth_callback_extracts_identity_and_names_connection(
        self, state_mgr, workspace_a
    ):
        integration_id = uuid4()
        state = await state_mgr.create_state(
            workspace_id=workspace_a,
            integration_id=integration_id,
            provider="google",
        )

        mock_conn = IntegrationConnection(
            id=integration_id,
            workspace_id=workspace_a,
            provider="google",
            name="Google Gmail",
            settings={},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conn
        db = AsyncMock()
        db.execute.return_value = mock_result

        full_scopes = f"{GOOGLE_CALENDAR_SCOPE} {GOOGLE_GMAIL_READONLY_SCOPE} {GOOGLE_GMAIL_SEND_SCOPE}"

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            "access_token": "valid_oauth_access_token",
            "refresh_token": "valid_oauth_refresh_token",
            "scope": full_scopes,
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch.object(
                 GoogleGmailOAuthProvider,
                 "get_account_identity",
                 return_value={
                     "email": "executive@originyx.com",
                     "display_name": "Executive Officer",
                     "provider_account_id": "google_sub_999",
                     "metadata": {"messages_total": 512},
                 },
             ):
            mock_post.return_value = mock_post_resp

            res = await oauth_callback(
                request=AsyncMock(spec=Request),
                state=state,
                code="google_auth_code_xyz",
                db=db,
                state_manager=state_mgr,
            )

            assert res["status"] == "success"
            assert mock_conn.status == ConnectionStatus.CONNECTED.value
            assert mock_conn.name == "Google Gmail (executive@originyx.com)"
            assert mock_conn.settings["email"] == "executive@originyx.com"
            assert mock_conn.settings["display_name"] == "Executive Officer"
            assert mock_conn.settings["provider_account_id"] == "google_sub_999"
            assert mock_conn.credentials_json.get("__encrypted__") is True

    async def test_oauth_callback_uses_configured_redirect_uri(
        self, state_mgr, workspace_a
    ):
        """Verifies callback uses GOOGLE_REDIRECT_URI / MICROSOFT_REDIRECT_URI over request.url_for."""
        # 1. Google test with configured HTTPS redirect URI behind HTTP proxy
        g_id = uuid4()
        g_state = await state_mgr.create_state(workspace_id=workspace_a, integration_id=g_id, provider="google")
        g_conn = IntegrationConnection(id=g_id, workspace_id=workspace_a, provider="google", settings={})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = g_conn
        db = AsyncMock()
        db.execute.return_value = mock_result

        # Request behind reverse proxy generated HTTP URL
        http_request = AsyncMock(spec=Request)
        http_request.url_for.return_value = "http://webhook.originyx.in/api/v1/integrations/oauth/callback"

        configured_https_redirect = "https://webhook.originyx.in/api/v1/integrations/oauth/callback"

        mock_post_resp = MagicMock(status_code=200)
        mock_post_resp.json.return_value = {
            "access_token": "g_tok",
            "refresh_token": "g_ref",
            "scope": f"{GOOGLE_CALENDAR_SCOPE} {GOOGLE_GMAIL_READONLY_SCOPE} {GOOGLE_GMAIL_SEND_SCOPE}",
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("app.domain.integration.router.get_settings") as mock_settings, \
             patch.object(GoogleGmailOAuthProvider, "get_account_identity", return_value={"email": "u@g.com"}):
            mock_settings.return_value.google_client_id = "g_cid"
            mock_settings.return_value.google_client_secret = "g_sec"
            mock_settings.return_value.google_redirect_uri = configured_https_redirect
            mock_settings.return_value.microsoft_redirect_uri = None
            mock_settings.return_value.microsoft_tenant_id = "common"
            mock_post.return_value = mock_post_resp

            await oauth_callback(
                request=http_request,
                state=g_state,
                code="g_code",
                db=db,
                state_manager=state_mgr,
            )

            # Assert the token exchange POST request used the configured HTTPS redirect URI
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["data"]["redirect_uri"] == configured_https_redirect

        # 2. Microsoft test with configured redirect URI
        ms_id = uuid4()
        ms_state = await state_mgr.create_state(workspace_id=workspace_a, integration_id=ms_id, provider="microsoft")
        ms_conn = IntegrationConnection(id=ms_id, workspace_id=workspace_a, provider="microsoft", settings={})
        mock_result.scalar_one_or_none.return_value = ms_conn

        ms_redirect = "https://webhook.originyx.in/api/v1/integrations/oauth/callback"
        ms_post_resp = MagicMock(status_code=200)
        ms_post_resp.json.return_value = {
            "access_token": "ms_tok",
            "refresh_token": "ms_ref",
            "scope": f"{MICROSOFT_CALENDAR_SCOPE} {MICROSOFT_MAIL_READ_SCOPE} {MICROSOFT_MAIL_SEND_SCOPE}",
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("app.domain.integration.router.get_settings") as mock_settings, \
             patch.object(MicrosoftGraphOAuthProvider, "get_account_identity", return_value={"email": "u@ms.com"}):
            mock_settings.return_value.microsoft_client_id = "ms_cid"
            mock_settings.return_value.microsoft_client_secret = "ms_sec"
            mock_settings.return_value.microsoft_redirect_uri = ms_redirect
            mock_settings.return_value.google_redirect_uri = None
            mock_settings.return_value.microsoft_tenant_id = "common"
            mock_post.return_value = ms_post_resp

            await oauth_callback(
                request=http_request,
                state=ms_state,
                code="ms_code",
                db=db,
                state_manager=state_mgr,
            )

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["data"]["redirect_uri"] == ms_redirect
