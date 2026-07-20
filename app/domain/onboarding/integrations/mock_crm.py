from typing import List, Dict, Any
from app.domain.onboarding.integrations.registry import ConnectorCapability, ConnectorRegistry

class MockCRMAdapter(ConnectorCapability):
    """
    Mock adapter to simulate syncing from Salesforce/HubSpot during onboarding.
    """
    
    @property
    def supported_entities(self) -> List[str]:
        return ["CUSTOMER", "LEAD", "OPPORTUNITY", "ACTIVITY"]

    def fetch_batch(self, entity_type: str) -> List[Dict[str, Any]]:
        # Mocking messy data to test the DataQualityEngine
        if entity_type == "CUSTOMER":
            return [
                {"external_id": "C001", "name": "Acme Corp", "email": "contact@acme.com", "phone": "555-0100"},
                {"external_id": "C002", "name": "Globex", "email": None, "phone": "555-0200"}, # Missing email
                {"external_id": "C003", "name": "Soylent", "email": "info@soylent.com", "phone": None}, # Missing phone
                {"external_id": "C001", "name": "Acme Corp (Duplicate)", "email": "contact@acme.com", "phone": "555-0100"} # Duplicate
            ]
        return []

# Register the mock adapter
ConnectorRegistry.register("MOCK_CRM", MockCRMAdapter)
