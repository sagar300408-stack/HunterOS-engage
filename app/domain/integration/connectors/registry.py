from typing import Dict, List, Optional

from app.domain.integration.connectors.base import BaseConnector


class ConnectorRegistry:
    """
    Registry for Enterprise Integration Connectors.
    """
    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        self._connectors[connector.metadata.connector_id] = connector

    def get_connector(self, connector_id: str) -> Optional[BaseConnector]:
        return self._connectors.get(connector_id)
        
    def get_all_connectors(self) -> List[BaseConnector]:
        return list(self._connectors.values())


connector_registry = ConnectorRegistry()
