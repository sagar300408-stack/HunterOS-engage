from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession
from app.events.model.actor_types import ActorType
from app.events.model.integration_types import IntegrationType

class ResolvedContext(BaseModel):
    integration: IntegrationType
    workspace_id: UUID
    actor_type: ActorType
    customer_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    
    # Future Enrichment Fields
    # language: Optional[str] = None
    # timezone: Optional[str] = None
    # sales_rep: Optional[UUID] = None
    # campaign: Optional[str] = None

class IntegrationContextResolver(ABC):
    @abstractmethod
    async def resolve(self, session: AsyncSession, payload: Dict[str, Any]) -> ResolvedContext:
        """Resolves an external integration payload into a fully enriched application context."""
        pass
