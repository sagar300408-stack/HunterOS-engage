from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.events.model.integration_types import IntegrationType
from app.application.context.interfaces import IntegrationContextResolver, ResolvedContext
from app.application.context.exceptions import UnregisteredIntegrationError

class ContextResolutionService:
    def __init__(self):
        self._resolvers: Dict[IntegrationType, IntegrationContextResolver] = {}

    def register(self, integration: IntegrationType, resolver: IntegrationContextResolver) -> None:
        """Register a resolver for a specific integration type."""
        self._resolvers[integration] = resolver

    async def resolve(
        self, session: AsyncSession, integration: IntegrationType, payload: Dict[str, Any]
    ) -> ResolvedContext:
        """Find the exact resolver in O(1) time and resolve the context."""
        resolver = self._resolvers.get(integration)
        if not resolver:
            raise UnregisteredIntegrationError(f"No resolver registered for {integration.value}")
        return await resolver.resolve(session, payload)
