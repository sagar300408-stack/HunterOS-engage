from app.domain.integration.connectors.registry import connector_registry
from app.domain.integration.connectors.mocks import MockCRMConnector, MockEmailConnector, MockSlackConnector


def bootstrap_integrations():
    """
    Registers all standard connectors in the global registry.
    """
    connector_registry.register(MockCRMConnector())
    connector_registry.register(MockEmailConnector())
    connector_registry.register(MockSlackConnector())
