"""
HunterOS Engage — Graph Projections Engine (Phase 2.1.4)

Coordinates projection generation by querying read repositories and delegating to ProjectionRegistry.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from app.domain.memory.graph.models import EntityReference, GraphNodeType
from app.domain.memory.graph.projections.registry import (
    GraphProjectionRegistry,
    default_projection_registry,
)
from app.domain.memory.graph.repository import GraphReadRepository
from app.domain.memory.graph.schemas import (
    Customer360Response,
    CustomGraphResponse,
    OpportunityNetworkResponse,
    OrganizationResponse,
    PropertyNetworkResponse,
)


class GraphProjectionEngine:
    """
    Engine for generating domain-specific graph views and projections.
    """

    def __init__(
        self,
        read_repository: GraphReadRepository,
        projection_registry: Optional[GraphProjectionRegistry] = None,
    ) -> None:
        self._read_repo = read_repository
        self._registry = projection_registry or default_projection_registry

    async def project(
        self,
        projection_name: str,
        workspace_id: Optional[uuid.UUID],
        entity_type: GraphNodeType | str,
        entity_id: str,
        max_depth: int = 2,
        session: Any = None,
    ) -> Any:
        """Run named projection rooted at given entity."""
        all_edges = await self._read_repo.get_all_active_edges_for_workspace(
            workspace_id=workspace_id,
            session=session,
        )

        n_type = entity_type if isinstance(entity_type, GraphNodeType) else GraphNodeType(entity_type)
        root_ref = EntityReference(
            entity_type=n_type,
            entity_id=entity_id,
            workspace_id=workspace_id,
        )

        proj = self._registry.get_projection(projection_name)
        return proj.project(all_edges, root_ref, max_depth=max_depth)

    async def project_customer_360(
        self,
        workspace_id: Optional[uuid.UUID],
        customer_id: str | uuid.UUID,
        session: Any = None,
    ) -> Customer360Response:
        """Generate Customer 360 Knowledge Graph view."""
        return await self.project(
            projection_name="customer_360",
            workspace_id=workspace_id,
            entity_type=GraphNodeType.CUSTOMER,
            entity_id=str(customer_id),
            session=session,
        )

    async def project_organization(
        self,
        workspace_id: Optional[uuid.UUID],
        company_id: str | uuid.UUID,
        session: Any = None,
    ) -> OrganizationResponse:
        """Generate Company Organization Graph view."""
        return await self.project(
            projection_name="organization",
            workspace_id=workspace_id,
            entity_type=GraphNodeType.COMPANY,
            entity_id=str(company_id),
            session=session,
        )

    async def project_property_network(
        self,
        workspace_id: Optional[uuid.UUID],
        property_id: str | uuid.UUID,
        session: Any = None,
    ) -> PropertyNetworkResponse:
        """Generate Property Network Graph view."""
        return await self.project(
            projection_name="property_network",
            workspace_id=workspace_id,
            entity_type=GraphNodeType.PROPERTY,
            entity_id=str(property_id),
            session=session,
        )

    async def project_opportunity_network(
        self,
        workspace_id: Optional[uuid.UUID],
        opportunity_id: str | uuid.UUID,
        session: Any = None,
    ) -> OpportunityNetworkResponse:
        """Generate Opportunity Deal Network Graph view."""
        return await self.project(
            projection_name="opportunity_network",
            workspace_id=workspace_id,
            entity_type=GraphNodeType.OPPORTUNITY,
            entity_id=str(opportunity_id),
            session=session,
        )

    async def project_custom(
        self,
        workspace_id: Optional[uuid.UUID],
        entity_type: GraphNodeType | str,
        entity_id: str,
        max_depth: int = 2,
        session: Any = None,
    ) -> CustomGraphResponse:
        """Generate Custom Graph projection."""
        return await self.project(
            projection_name="custom",
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            max_depth=max_depth,
            session=session,
        )


__all__ = [
    "GraphProjectionEngine",
]
