import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.future import select

from app.domain.collaboration.models import (
    CollaborationTask,
    TaskEscalation,
    TaskStatus
)
from app.domain.collaboration.repository import CollaborationRepository

class EscalationEngine:
    """
    Detects tasks that are stalled or where assigned resources are unavailable, 
    and automatically escalates them.
    """

    @classmethod
    async def escalate_task(
        cls, 
        repo: CollaborationRepository, 
        task: CollaborationTask, 
        reason: str, 
        escalated_to_role: str
    ) -> TaskEscalation:
        """
        Escalates a task to a higher tier.
        """
        escalation = TaskEscalation(
            task_id=task.id,
            reason=reason,
            escalated_to_role=escalated_to_role
        )
        
        task.status = TaskStatus.ESCALATED
        task.updated_at = datetime.now(timezone.utc)
        
        repo.session.add(escalation)
        await repo.session.commit()
        await repo.session.refresh(escalation)
        
        return escalation
