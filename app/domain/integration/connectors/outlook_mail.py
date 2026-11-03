import logging
from typing import Any, Dict, List, Optional, Tuple

from app.domain.integration.connectors.base import BaseConnector
from app.domain.integration.email_auth.provider import MicrosoftGraphOAuthProvider
from app.domain.integration.models import ConnectionStatus
from app.domain.integration.schemas import ConnectorCapabilities, ConnectorMetadata

logger = logging.getLogger("hunteros.integration.connectors.outlook_mail")


class OutlookEmailConnector(BaseConnector):
    """
    Production connector for Microsoft Outlook / Microsoft 365 Mail.
    Provides connectivity verification, OAuth account identity, and health checks.
    """

    def __init__(self, tenant_id: str = "common"):
        self._tenant_id = tenant_id or "common"
        self._provider = MicrosoftGraphOAuthProvider(tenant_id=self._tenant_id)

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            connector_id="outlook_mail_v1",
            connector_type="email",
            provider="microsoft",
            name="Microsoft Outlook",
            version="1.0.0",
            description="Microsoft Outlook / 365 integration for mailbox automation, reading, and sending.",
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
        Validates real Microsoft Graph API connectivity.
        If access token returns 401 and refresh_token exists, attempts single token refresh and re-test.
        """
        access_token = credentials.get("access_token")
        if not access_token:
            return ConnectionStatus.ERROR.value, "Missing access token in credentials"

        tenant_id = (settings or {}).get("tenant_id") or self._tenant_id
        provider = MicrosoftGraphOAuthProvider(tenant_id=tenant_id) if tenant_id != self._tenant_id else self._provider

        is_connected, error_msg = await provider.check_connectivity(access_token)
        if is_connected:
            return ConnectionStatus.CONNECTED.value, None

        # If 401 and refresh token available, attempt refresh once
        refresh_token = credentials.get("refresh_token")
        if refresh_token and error_msg and ("401" in error_msg or "denied" in error_msg.lower()):
            from app.config import get_settings
            app_settings = get_settings()
            client_id = app_settings.microsoft_client_id or (settings or {}).get("client_id")
            client_secret = app_settings.microsoft_client_secret or (settings or {}).get("client_secret")

            if client_id and client_secret:
                try:
                    new_tokens = await provider.refresh_token(
                        client_id=client_id,
                        client_secret=client_secret,
                        refresh_token=refresh_token,
                    )
                    retry_connected, retry_err = await provider.check_connectivity(new_tokens["access_token"])
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

        tenant_id = (settings or {}).get("tenant_id") or self._tenant_id
        provider = MicrosoftGraphOAuthProvider(tenant_id=tenant_id) if tenant_id != self._tenant_id else self._provider

        if action_name == "check_connectivity":
            is_conn, err = await provider.check_connectivity(access_token)
            return {"status": "success" if is_conn else "error", "connected": is_conn, "error": err}

        elif action_name == "get_account_identity":
            identity = await provider.get_account_identity(access_token)
            return {"status": "success", "identity": identity}

        raise ValueError(f"Action '{action_name}' not supported by OutlookEmailConnector")

    async def sync_events(self, credentials: Dict[str, Any], last_sync: Any) -> list:
        # Ingestion logic belongs to E2
        return []

    async def parse_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> list:
        return []
