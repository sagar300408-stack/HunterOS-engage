import uuid
from typing import List

from app.domain.context.models import KnowledgeGraphEdge, EntityType
from app.domain.context.repository import ContextRepository

class KnowledgeGraphEngine:
    """
    Manages relationship edges between disparate entities.
    """

    @classmethod
    async def connect_entities(
        cls, 
        repo: ContextRepository, 
        workspace_id: uuid.UUID,
        source_id: uuid.UUID, 
        source_type: EntityType,
        target_id: uuid.UUID,
        target_type: EntityType,
        relationship: str,
        source_system: str,
        confidence: float = 1.0
    ) -> KnowledgeGraphEdge:
        
        edge = KnowledgeGraphEdge(
            workspace_id=workspace_id,
            source_entity_id=source_id,
            source_entity_type=source_type,
            target_entity_id=target_id,
            target_entity_type=target_type,
            relationship_type=relationship,
            source_system=source_system,
            confidence_score=confidence
        )
        return await repo.save_edge(edge)
        
    @classmethod
    async def get_related_entities(
        cls, 
        repo: ContextRepository, 
        entity_id: uuid.UUID,
        max_depth: int = 1
    ) -> List[KnowledgeGraphEdge]:
        
        # Guard depth due to context budget
        if max_depth > 3:
            max_depth = 3
            
        # Simplified traversal for depth=1
        return await repo.get_edges_for_entity(entity_id, max_depth)
