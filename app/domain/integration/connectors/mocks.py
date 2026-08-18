from typing import Dict, Any, Tuple, Optional

from app.domain.integration.connectors.base import BaseConnector
from app.domain.integration.schemas import ConnectorMetadata, ConnectorCapabilities
from app.domain.integration.models import ConnectionStatus


class MockCRMConnector(BaseConnector):
    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            connector_id="mock_crm_v1",
            connector_type="crm",
            provider="mock_crm",
            name="Mock CRM",
            version="1.0.0",
            description="A mock CRM connector for testing the integration framework.",
            capabilities=ConnectorCapabilities(supports_read=True, supports_write=True, supports_webhooks=False),
            authentication_type="api_key",
            supported_actions=["create_lead", "update_opportunity"],
            supported_events=["lead_created", "opportunity_won"]
        )

    async def health_check(self, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        if credentials.get("api_key") == "valid_key":
            return ConnectionStatus.CONNECTED.value, None
        elif credentials.get("api_key") == "degraded_key":
            return ConnectionStatus.DEGRADED.value, "API rate limits nearing capacity."
        return ConnectionStatus.ERROR.value, "Invalid API key provided."

    async def execute_action(self, action_name: str, payload: Dict[str, Any], credentials: Dict[str, Any], settings: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"status": "success", "mock_action": action_name, "id": "mock_123"}

    async def sync_events(self, credentials: Dict[str, Any], last_sync: Any) -> list:
        return []

    async def parse_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> list:
        return []


class MockEmailConnector(BaseConnector):
    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            connector_id="mock_email_v1",
            connector_type="email",
            provider="mock_email",
            name="Mock Email Provider",
            version="1.0.0",
            description="A mock email provider for testing.",
            capabilities=ConnectorCapabilities(supports_read=False, supports_write=True, supports_webhooks=True),
            authentication_type="oauth2",
            supported_actions=["send_email"],
            supported_events=["email_opened", "email_bounced"]
        )

    async def health_check(self, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        if credentials.get("access_token"):
            return ConnectionStatus.CONNECTED.value, None
        return ConnectionStatus.ERROR.value, "Missing access token."

    async def execute_action(self, action_name: str, payload: Dict[str, Any], credentials: Dict[str, Any], settings: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"status": "success", "message_id": "mock_msg_456"}

    async def sync_events(self, credentials: Dict[str, Any], last_sync: Any) -> list:
        return []

    async def parse_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> list:
        return []


class MockSlackConnector(BaseConnector):
    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            connector_id="mock_slack_v1",
            connector_type="messaging",
            provider="mock_slack",
            name="Mock Slack Provider",
            version="1.0.0",
            description="A mock Slack provider for testing.",
            capabilities=ConnectorCapabilities(supports_read=True, supports_write=True, supports_webhooks=True),
            authentication_type="oauth2",
            supported_actions=["send_message", "create_channel"],
            supported_events=["message_received"]
        )

    async def health_check(self, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        if credentials.get("bot_token"):
            return ConnectionStatus.CONNECTED.value, None
        return ConnectionStatus.ERROR.value, "Missing bot token."

    async def execute_action(self, action_name: str, payload: Dict[str, Any], credentials: Dict[str, Any], settings: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"status": "success", "channel_id": "mock_chan_789"}

    async def sync_events(self, credentials: Dict[str, Any], last_sync: Any) -> list:
        return []

    async def parse_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> list:
        return []
