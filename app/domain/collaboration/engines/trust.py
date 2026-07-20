import uuid
from typing import Dict, Any
from sqlalchemy.future import select
from sqlalchemy import func

from app.domain.collaboration.models import (
    CollaborationTask,
    TaskFeedback,
    AutonomyLevel
)
from app.domain.collaboration.repository import CollaborationRepository

class TrustEngine:
    """
    Measures how often AI makes the correct decision vs how often it is overridden by humans.
    Generates the 'Accuracy' executive KPI.
    """

    @classmethod
    async def measure_accuracy(cls, repo: CollaborationRepository, workspace_id: uuid.UUID) -> Dict[str, Any]:
        """
        Returns stats about AI decisions and accuracy.
        """
        
        # 1. Total AI decisions (where AI_OWNED)
        total_ai_result = await repo.session.execute(
            select(func.count(CollaborationTask.id))
            .where(
                CollaborationTask.workspace_id == workspace_id,
                CollaborationTask.ownership == AutonomyLevel.AI_OWNED
            )
        )
        total_ai_decisions = total_ai_result.scalar() or 0
        
        # 2. Total overrides on AI decisions
        # We find feedbacks where is_override is true, linked to AI_OWNED tasks.
        overrides_result = await repo.session.execute(
            select(func.count(TaskFeedback.id))
            .join(CollaborationTask, TaskFeedback.task_id == CollaborationTask.id)
            .where(
                CollaborationTask.workspace_id == workspace_id,
                CollaborationTask.ownership == AutonomyLevel.AI_OWNED,
                TaskFeedback.is_override == True
            )
        )
        total_overrides = overrides_result.scalar() or 0
        
        correct_decisions = total_ai_decisions - total_overrides
        
        accuracy = 100.0
        if total_ai_decisions > 0:
            accuracy = (correct_decisions / total_ai_decisions) * 100.0
            
        return {
            "ai_decisions": total_ai_decisions,
            "human_overrides": total_overrides,
            "correct": correct_decisions,
            "accuracy_percentage": round(accuracy, 2)
        }
