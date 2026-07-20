import uuid
from typing import List, Optional, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, update

from app.domain.context.models import (
    CustomerContext,
    BusinessOntology,
    KnowledgeGraphEdge,
    ContextConflict,
    ConflictStatus,
    EntityType
)

class ContextRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_entity(self, model: Type, entity_id: uuid.UUID) -> Optional[Any]:
        result = await self.session.execute(
            select(model).where(model.id == entity_id, model.is_active == True)
        )
        return result.scalars().first()
        
    async def get_ontology_map(self, workspace_id: uuid.UUID) -> dict:
        result = await self.session.execute(
            select(BusinessOntology).where(
                BusinessOntology.workspace_id == workspace_id,
                BusinessOntology.is_active == True
            )
        )
        ontologies = result.scalars().all()
        return {o.internal_concept: o.display_term for o in ontologies}

    async def get_edges_for_entity(self, entity_id: uuid.UUID, max_depth: int = 1) -> List[KnowledgeGraphEdge]:
        # For Milestone 4, we support depth=1 directly here. 
        # A true depth>1 requires recursive CTEs or multiple queries in retrieval engine.
        result = await self.session.execute(
            select(KnowledgeGraphEdge).where(
                or_(
                    KnowledgeGraphEdge.source_entity_id == entity_id,
                    KnowledgeGraphEdge.target_entity_id == entity_id
                )
            )
        )
        return result.scalars().all()

    async def save_conflict(self, conflict: ContextConflict) -> ContextConflict:
        self.session.add(conflict)
        await self.session.commit()
        await self.session.refresh(conflict)
        return conflict

    async def list_unresolved_conflicts(self, workspace_id: uuid.UUID) -> List[ContextConflict]:
        result = await self.session.execute(
            select(ContextConflict).where(
                ContextConflict.workspace_id == workspace_id,
                ContextConflict.status == ConflictStatus.UNRESOLVED
            )
        )
        return result.scalars().all()

    async def save_entity(self, entity: Any) -> Any:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
        
    async def save_edge(self, edge: KnowledgeGraphEdge) -> KnowledgeGraphEdge:
        self.session.add(edge)
        await self.session.commit()
        await self.session.refresh(edge)
        return edge
