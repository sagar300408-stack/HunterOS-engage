import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.customer_success.models import SuccessPlaybook

logger = logging.getLogger("hunteros.cs")

class PlaybookEngine:
    """
    Triggers and manages standardized success playbooks.
    """

    @staticmethod
    async def trigger_playbook(db: AsyncSession, workspace_id: uuid.UUID, playbook_name: str, reason: str) -> SuccessPlaybook:
        """
        Triggers a new playbook (e.g. 'Low Adoption' due to dropping Health Score).
        """
        # In a real system, tasks_json would be pre-populated from a template library
        playbook = SuccessPlaybook(
            workspace_id=workspace_id,
            name=playbook_name,
            trigger_reason=reason,
            tasks_json=[
                {"task": "Analyze adoption drop-off", "status": "pending"},
                {"task": "Schedule executive sync", "status": "pending"}
            ]
        )
        db.add(playbook)
        await db.commit()
        await db.refresh(playbook)
        
        logger.warning(f"Triggered '{playbook_name}' playbook for Workspace {workspace_id}. Reason: {reason}")
        return playbook
