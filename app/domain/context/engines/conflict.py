import uuid
from typing import Any, Dict
from app.domain.context.models import ContextConflict, EntityType
from app.domain.context.repository import ContextRepository

class ContextConflictEngine:
    """
    Detects and reconciles inconsistent data from multiple sources.
    """

    @classmethod
    async def detect_conflict(
        cls, 
        repo: ContextRepository,
        workspace_id: uuid.UUID,
        entity_id: uuid.UUID,
        entity_type: EntityType,
        field_name: str,
        current_source: str,
        current_value: Any,
        new_source: str,
        new_value: Any
    ) -> bool:
        """
        If a conflict exists, logs it and returns True.
        """
        if current_value == new_value:
            return False
            
        # Log conflict for manual or heuristic resolution later
        conflict = ContextConflict(
            workspace_id=workspace_id,
            entity_id=entity_id,
            entity_type=entity_type,
            field_name=field_name,
            source_a=current_source,
            value_a=current_value,
            source_b=new_source,
            value_b=new_value
        )
        
        await repo.save_conflict(conflict)
        return True
