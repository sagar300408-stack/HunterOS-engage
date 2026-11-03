from app.domain.integration.connectors.registry import connector_registry
from app.domain.integration.connectors.mocks import MockCRMConnector, MockEmailConnector, MockSlackConnector
from app.domain.integration.connectors.gmail import GmailEmailConnector
from app.domain.integration.connectors.outlook_mail import OutlookEmailConnector


def bootstrap_integrations():
    """
    Registers all standard connectors in the global registry.
    """
    connector_registry.register(MockCRMConnector())
    connector_registry.register(MockEmailConnector())
    connector_registry.register(MockSlackConnector())
    connector_registry.register(GmailEmailConnector())
    connector_registry.register(OutlookEmailConnector())
