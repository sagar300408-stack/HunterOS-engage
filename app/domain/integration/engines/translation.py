import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.domain.integration.engines.registry import IntegrationRegistry
from app.domain.integration.models import IntegrationConnection

logger = logging.getLogger("hunteros.integration")

class EventTranslationEngine:
    """
    Normalizes external events (e.g. Salesforce Lead Created) into generic HunterOS business events.
    """

    @staticmethod
    async def translate_webhook_event(
        db: AsyncSession, 
        integration: IntegrationConnection, 
        payload: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Takes raw vendor webhook payload, delegates to the connector's parse_webhook,
        and translates the resulting generic event to the Event Bus.
        """
        connector = IntegrationRegistry.get_connector(integration.connector_id)
        
        # 1. Vendor specific parsing
        raw_events = await connector.parse_webhook(payload, headers)
        
        normalized_events = []
        for raw_event in raw_events:
            # 2. Schema Translation (mocked here, delegates to MappingEngine usually)
            normalized = {
                "event_id": str(uuid.uuid4()),
                "source": integration.connector_id,
                "workspace_id": str(integration.workspace_id),
                "event_type": raw_event.get("event_type", "unknown"),
                "data": raw_event.get("data", {})
            }
            normalized_events.append(normalized)
            
            # Here we would publish `normalized` to the HunterOS Event Bus
            logger.info(f"Translated event from {integration.connector_id}: {normalized['event_type']}")
            
        return normalized_events
