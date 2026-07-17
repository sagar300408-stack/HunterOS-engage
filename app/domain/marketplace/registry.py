from typing import List, Dict, Optional
from uuid import UUID

from app.domain.marketplace.models import InstalledConnector, ConnectorDefinition
from app.domain.marketplace.repository import MarketplaceRepository


class ConnectorCapabilityRegistry:
    def __init__(self, repo: MarketplaceRepository):
        self.repo = repo

    async def get_connectors_by_capability(self, workspace_id: UUID, capability: str) -> List[Dict]:
        """
        The primary mechanism for execution lookup.
        Finds all enabled installed connectors in the workspace that support the given capability.
        Returns a list of dicts containing the installation and its definition.
        """
        installed = await self.repo.get_installed_connectors(workspace_id)
        
        results = []
        for installation in installed:
            if not installation.enabled:
                continue
                
            definition = await self.repo.get_connector_definition(installation.connector_id)
            if not definition or definition.status != "ACTIVE":
                continue
                
            if capability in definition.supported_capabilities:
                results.append({
                    "installation": installation,
                    "definition": definition
                })
                
        return results
