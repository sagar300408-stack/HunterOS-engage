import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.domain.integration.connectors.base import BaseConnector
from app.domain.integration.email_auth.provider import GoogleGmailOAuthProvider
from app.domain.integration.models import ConnectionStatus
from app.domain.integration.schemas import ConnectorCapabilities, ConnectorMetadata

logger = logging.getLogger("hunteros.integration.connectors.gmail")


class GmailEmailConnector(BaseConnector):
    """
    Production connector for Google Gmail.
    Provides connectivity verification, OAuth account identity, and health checks.
    """

    def __init__(self):
        self._provider = GoogleGmailOAuthProvider()

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            connector_id="google_gmail_v1",
            connector_type="email",
            provider="google",
            name="Google Gmail",
            version="1.0.0",
            description="Google Gmail integration for mailbox automation, reading, and sending.",
            capabilities=ConnectorCapabilities(
                supports_read=True,
                supports_write=True,
                supports_webhooks=False,
            ),
            authentication_type="oauth2",
            supported_actions=["check_connectivity", "get_account_identity"],
            supported_events=["email_received"],
        )

    async def health_check(self, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        """
        Validates real Gmail API connectivity.
        If access token returns 401 and refresh_token exists, attempts single token refresh and re-test.
        """
        access_token = credentials.get("access_token")
        if not access_token:
            return ConnectionStatus.ERROR.value, "Missing access token in credentials"

        is_connected, error_msg = await self._provider.check_connectivity(access_token)
        if is_connected:
            return ConnectionStatus.CONNECTED.value, None

        # If 401 and refresh token available, attempt refresh once
        refresh_token = credentials.get("refresh_token")
        if refresh_token and error_msg and "401" in error_msg:
            from app.config import get_settings
            app_settings = get_settings()
            client_id = app_settings.google_client_id or settings.get("client_id")
            client_secret = app_settings.google_client_secret or settings.get("client_secret")

            if client_id and client_secret:
                try:
                    new_tokens = await self._provider.refresh_token(
                        client_id=client_id,
                        client_secret=client_secret,
                        refresh_token=refresh_token,
                    )
                    retry_connected, retry_err = await self._provider.check_connectivity(new_tokens["access_token"])
                    if retry_connected:
                        return ConnectionStatus.CONNECTED.value, None
                    return ConnectionStatus.ERROR.value, retry_err
                except Exception as e:
                    return ConnectionStatus.ERROR.value, f"Token refresh failed during health check: {e}"

        return ConnectionStatus.ERROR.value, error_msg

    async def execute_action(
        self,
        action_name: str,
        payload: Dict[str, Any],
        credentials: Dict[str, Any],
        settings: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Executes supported provider actions.
        """
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError("Missing access token for action execution")

        if action_name == "check_connectivity":
            is_conn, err = await self._provider.check_connectivity(access_token)
            return {"status": "success" if is_conn else "error", "connected": is_conn, "error": err}

        elif action_name == "get_account_identity":
            identity = await self._provider.get_account_identity(access_token)
            return {"status": "success", "identity": identity}

        raise ValueError(f"Action '{action_name}' not supported by GmailEmailConnector")

    async def sync_events(self, credentials: Dict[str, Any], last_sync: Any) -> list:
        # Ingestion logic belongs to E2
        return []

    async def parse_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> list:
        return []
