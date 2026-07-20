import abc
from typing import Dict, Any, Tuple, Optional

from app.domain.integration.schemas import ConnectorMetadata


class BaseConnector(abc.ABC):
    """
    Abstract interface for all external system connectors.
    """
    
    @property
    @abc.abstractmethod
    def metadata(self) -> ConnectorMetadata:
        """
        Returns the structured metadata defining this connector.
        """
        pass

    @abc.abstractmethod
    async def health_check(self, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        """
        Checks the health of the connection.
        Returns a tuple: (status_string, error_message).
        Status string must match ConnectionStatus values (connected, degraded, error).
        """
        pass

    @abc.abstractmethod
    async def execute_action(self, action_name: str, payload: Dict[str, Any], credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a supported action. (To be fully utilized in Milestone 9.2).
        """
        pass

    @abc.abstractmethod
    async def sync_events(self, credentials: Dict[str, Any], last_sync: Any) -> list:
        """
        Pulls events from the external system. (To be fully utilized in Milestone 9.4).
        """
        pass

    @abc.abstractmethod
    async def parse_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> list:
        """
        Parses a vendor-specific webhook payload into a list of normalized event dictionaries.
        """
        pass
