import logging
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.customer_success.models import CustomerLifecycle, LifecycleStage

logger = logging.getLogger("hunteros.cs")

class LifecycleEngine:
    """
    Manages the overarching customer lifecycle stages.
    """

    @staticmethod
    async def get_or_create_lifecycle(db: AsyncSession, workspace_id: uuid.UUID) -> CustomerLifecycle:
        stmt = select(CustomerLifecycle).where(CustomerLifecycle.workspace_id == workspace_id)
        result = await db.execute(stmt)
        lifecycle = result.scalar_one_or_none()
        
        if not lifecycle:
            lifecycle = CustomerLifecycle(workspace_id=workspace_id)
            db.add(lifecycle)
            await db.commit()
            await db.refresh(lifecycle)
            
        return lifecycle

    @staticmethod
    async def advance_stage(db: AsyncSession, workspace_id: uuid.UUID, new_stage: LifecycleStage) -> CustomerLifecycle:
        lifecycle = await LifecycleEngine.get_or_create_lifecycle(db, workspace_id)
        
        if lifecycle.current_stage != new_stage:
            lifecycle.current_stage = new_stage
            lifecycle.stage_entered_at = datetime.utcnow()
            await db.commit()
            logger.info(f"Workspace {workspace_id} advanced to Lifecycle Stage: {new_stage}")
            
        return lifecycle
