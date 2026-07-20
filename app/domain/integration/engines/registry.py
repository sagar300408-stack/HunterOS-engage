from typing import Dict, Any, Type
import logging
from app.domain.integration.connectors.base import BaseConnector

logger = logging.getLogger("hunteros.integration")

class IntegrationRegistry:
    """
    Maintains capabilities and metadata for all available connectors.
    """
    _connectors: Dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, connector_id: str, connector_class: Type[BaseConnector]):
        if connector_id in cls._connectors:
            logger.warning(f"Connector {connector_id} is already registered. Overwriting.")
        cls._connectors[connector_id] = connector_class
        logger.info(f"Registered connector: {connector_id}")

    @classmethod
    def get_connector(cls, connector_id: str) -> BaseConnector:
        connector_class = cls._connectors.get(connector_id)
        if not connector_class:
            raise ValueError(f"Connector {connector_id} not found in registry.")
        return connector_class()

    @classmethod
    def list_connectors(cls) -> list[str]:
        return list(cls._connectors.keys())
