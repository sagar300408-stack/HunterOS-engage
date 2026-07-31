import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.events.model.actor_types import ActorType
from app.events.model.integration_types import IntegrationType
from app.application.context.interfaces import IntegrationContextResolver, ResolvedContext

class WhatsAppContextResolver(IntegrationContextResolver):
    async def resolve(self, session: AsyncSession, payload: Dict[str, Any]) -> ResolvedContext:
        """
        Resolves a Meta WhatsApp webhook payload into the required HunterOS Application Context.
        
        Currently defaults to a single development workspace.
        In the future, this will perform a DB lookup:
        `SELECT workspace_id FROM whatsapp_accounts WHERE waba_id = payload['id']`
        """
        settings = get_settings()
        
        # 1. Resolve Workspace (Phase 1.2: Hardcoded to default workspace)
        # Eventually: extract waba_id = payload.get("entry", [{}])[0].get("id")
        workspace_id = uuid.UUID(settings.default_workspace_id)
        
        # 2. Resolve Actor Type
        # If the payload contains messages from a customer, it's CUSTOMER.
        # Otherwise, if it's a status update (delivered, read) or system ping, it's SYSTEM.
        actor_type = ActorType.SYSTEM
        
        try:
            entries = payload.get("entry", [])
            if entries:
                changes = entries[0].get("changes", [])
                if changes:
                    value = changes[0].get("value", {})
                    if "messages" in value:
                        actor_type = ActorType.CUSTOMER
        except Exception:
            pass # Default to SYSTEM on malformed payloads
            
        return ResolvedContext(
            integration=IntegrationType.WHATSAPP,
            workspace_id=workspace_id,
            actor_type=actor_type,
            customer_id=None,
            lead_id=None,
            conversation_id=None
        )
