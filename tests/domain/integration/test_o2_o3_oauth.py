import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.domain.integration.router import oauth_authorize, oauth_callback, OAUTH_STATE_CACHE
from app.domain.integration.models import IntegrationConnection
from fastapi import HTTPException
from starlette.requests import Request

@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db

@pytest.mark.asyncio
async def test_oauth_authorize_creates_valid_state(mock_db):
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
        result = await oauth_authorize(integration_id, workspace_id, request, mock_db)
        
        assert "authorize_url" in result
        assert "state=" in result["authorize_url"]
        
        # Verify state cache
        states = list(OAUTH_STATE_CACHE.keys())
        assert len(states) == 1
        state = states[0]
        
        cache_entry = OAUTH_STATE_CACHE[state]
        assert cache_entry["workspace_id"] == workspace_id
        assert cache_entry["integration_id"] == integration_id
        assert cache_entry["expires_at"] > datetime.now(timezone.utc)
        
    OAUTH_STATE_CACHE.clear()

@pytest.mark.asyncio
async def test_oauth_callback_consumes_state(mock_db):
    integration_id = uuid4()
    workspace_id = uuid4()
    state = "random-crypto-state"
    
    OAUTH_STATE_CACHE[state] = {
        "workspace_id": workspace_id,
        "integration_id": integration_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
    }
    
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
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"access_token": "test-token", "refresh_token": "test-refresh"}
        mock_post.return_value = mock_post_resp
        
        with patch("app.domain.integration.router.get_settings") as mock_settings:
            mock_settings.return_value.google_client_id = "test_client_id"
            mock_settings.return_value.google_client_secret = "test_client_secret"
            
            with patch("app.domain.integration.router.JsonCredentialProvider.store_credentials", new_callable=AsyncMock) as mock_store:
                
                result = await oauth_callback(request, state, "test-code", mock_db)
                
                assert result["status"] == "success"
                assert state not in OAUTH_STATE_CACHE
                mock_post.assert_called_once()
                mock_store.assert_called_once()
