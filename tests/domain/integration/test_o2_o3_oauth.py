import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
import urllib.parse
import fakeredis.aioredis as fake_redis

from app.domain.integration.router import (
    oauth_authorize,
    oauth_callback,
    OAUTH_STATE_CACHE,
    REQUIRED_GOOGLE_SCOPES,
    REQUIRED_MICROSOFT_SCOPES,
)
from app.domain.integration.models import IntegrationConnection
from app.domain.integration.oauth_state import OAuthStateManager
from app.domain.integration.credentials import EncryptedCredentialProvider
from fastapi import HTTPException
from starlette.requests import Request


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def redis_state_mgr():
    r = fake_redis.FakeRedis(decode_responses=True)
    return OAuthStateManager(redis_client=r)


@pytest.mark.asyncio
async def test_oauth_authorize_creates_valid_state(mock_db, redis_state_mgr):
    integration_id = uuid4()
    workspace_id = uuid4()
    
    mock_connection = IntegrationConnection(id=integration_id, workspace_id=workspace_id, provider="google")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_connection
    mock_db.execute.return_value = mock_result
    
    request = AsyncMock(spec=Request)
    request.url_for.return_value = "http://testserver/callback"
    
    with patch("app.domain.integration.router.get_settings") as mock_settings:
        mock_settings.return_value.google_client_id = "test_client_id"
        result = await oauth_authorize(
            integration_id=integration_id,
            workspace_id=workspace_id,
            request=request,
            db=mock_db,
            state_manager=redis_state_mgr,
        )
        
        assert "authorize_url" in result
        assert "state=" in result["authorize_url"]
        
        # P0-4: Verify Gmail scopes are present in authorize URL along with Calendar
        unquoted_url = urllib.parse.unquote(result["authorize_url"])
        assert "https://www.googleapis.com/auth/calendar.events" in unquoted_url
        assert "https://www.googleapis.com/auth/gmail.readonly" in unquoted_url
        assert "https://www.googleapis.com/auth/gmail.send" in unquoted_url
        
        # Verify state in Redis
        query_params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(result["authorize_url"]).query))
        state = query_params["state"]
        
        cache_entry = await redis_state_mgr.peek_state(state)
        assert cache_entry is not None
        assert cache_entry["workspace_id"] == str(workspace_id)
        assert cache_entry["integration_id"] == str(integration_id)
        assert cache_entry["provider"] == "google"


@pytest.mark.asyncio
async def test_oauth_callback_consumes_state(mock_db, redis_state_mgr):
    integration_id = uuid4()
    workspace_id = uuid4()
    
    state = await redis_state_mgr.create_state(
        workspace_id=workspace_id,
        integration_id=integration_id,
        provider="google",
        ttl_seconds=600,
    )
    
    mock_connection = IntegrationConnection(
        id=integration_id, 
        workspace_id=workspace_id, 
        provider="google",
        settings={}
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_connection
    mock_db.execute.return_value = mock_result
    
    request = AsyncMock(spec=Request)
    request.url_for.return_value = "http://testserver/callback"
    
    # Token response including all required scopes
    full_scopes = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send"
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            "access_token": "test-token",
            "refresh_token": "test-refresh",
            "scope": full_scopes,
        }
        mock_post.return_value = mock_post_resp
        
        with patch("app.domain.integration.router.get_settings") as mock_settings:
            mock_settings.return_value.google_client_id = "test_client_id"
            mock_settings.return_value.google_client_secret = "test_client_secret"
            
            result = await oauth_callback(
                request=request,
                state=state,
                code="test-code",
                db=mock_db,
                state_manager=redis_state_mgr,
            )
            
            assert result["status"] == "success"
            mock_post.assert_called_once()
            
            # P0-2: Verify state was consumed atomically from Redis
            peek_after = await redis_state_mgr.peek_state(state)
            assert peek_after is None
            
            # P0-1: Verify credentials stored encrypted
            assert mock_connection.credentials_json.get("__encrypted__") is True
            cred_provider = EncryptedCredentialProvider()
            decrypted = cred_provider.retrieve_credentials(mock_connection)
            assert decrypted["access_token"] == "test-token"
            assert decrypted["refresh_token"] == "test-refresh"
