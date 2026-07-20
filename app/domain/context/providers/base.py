from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class ContextProviderInterface(ABC):
    """
    Abstract interface for ingesting context from external systems (CRM, ERP, HRMS).
    All integrations must implement this interface to safely inject knowledge into HunterOS.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the source system (e.g., 'Salesforce CRM', 'Workday')."""
        pass
        
    @property
    @abstractmethod
    def provides_entities(self) -> List[str]:
        """List of EntityTypes this provider is authorized to update (e.g., ['CUSTOMER', 'TEAM_MEMBER'])."""
        pass

    @abstractmethod
    async def fetch_entity(self, entity_type: str, external_id: str) -> Optional[Dict[str, Any]]:
        """Fetches the current state of a specific entity from the external system."""
        pass

    @abstractmethod
    async def sync_all(self, entity_type: str) -> List[Dict[str, Any]]:
        """Batch fetches all active entities of a certain type to synchronize the knowledge graph."""
        pass
