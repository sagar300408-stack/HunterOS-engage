import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

from app.domain.analytics.models import FeatureAdoption

logger = logging.getLogger("hunteros.analytics")

class FeatureAdoptionEngine:
    """
    Tracks which specific capabilities (e.g., 'ai_approvals', 'friction_engine') are creating value.
    """

    @staticmethod
    async def record_usage(db: AsyncSession, workspace_id: uuid.UUID, feature_name: str):
        """
        Marks a feature as used, automatically recording 'first_used_at' and 'total_uses'.
        """
        stmt = select(FeatureAdoption).where(
            FeatureAdoption.workspace_id == workspace_id,
            FeatureAdoption.feature_name == feature_name
        )
        result = await db.execute(stmt)
        adoption = result.scalar_one_or_none()
        
        now = datetime.utcnow()
        if not adoption:
            adoption = FeatureAdoption(
                workspace_id=workspace_id,
                feature_name=feature_name,
                is_adopted=True,
                first_used_at=now,
                last_used_at=now,
                total_uses=1
            )
            db.add(adoption)
        else:
            adoption.last_used_at = now
            adoption.total_uses += 1
            if adoption.total_uses > 3: # Threshold for 'adopted'
                adoption.is_adopted = True
                
        await db.commit()
