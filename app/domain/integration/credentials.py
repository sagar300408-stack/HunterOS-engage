import abc
from typing import Dict, Any
from uuid import UUID

from app.domain.integration.models import IntegrationConnection


class CredentialProvider(abc.ABC):
    """
    Abstract interface for managing integration credentials securely.
    Ensures that the rest of HunterOS never accesses the raw JSON directly,
    allowing future migration to KMS or Vault.
    """
    
    @abc.abstractmethod
    def store_credentials(self, connection: IntegrationConnection, credentials: Dict[str, Any]) -> None:
        pass
        
    @abc.abstractmethod
    def retrieve_credentials(self, connection: IntegrationConnection) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def clear_credentials(self, connection: IntegrationConnection) -> None:
        pass


class JsonCredentialProvider(CredentialProvider):
    """
    Phase 9.1 implementation storing credentials as JSON in the database.
    """
    def store_credentials(self, connection: IntegrationConnection, credentials: Dict[str, Any]) -> None:
        connection.credentials_json = credentials
        
    def retrieve_credentials(self, connection: IntegrationConnection) -> Dict[str, Any]:
        return connection.credentials_json
        
    def clear_credentials(self, connection: IntegrationConnection) -> None:
        connection.credentials_json = {}
