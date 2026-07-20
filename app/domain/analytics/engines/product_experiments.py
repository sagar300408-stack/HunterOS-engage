import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import hashlib

from app.domain.analytics.models import ProductExperiment

logger = logging.getLogger("hunteros.analytics")

class ProductExperimentEngine:
    """
    Manages A/B testing assignments for workspaces and users.
    """

    @staticmethod
    async def get_variant(db: AsyncSession, experiment_name: str, workspace_id: uuid.UUID = None, user_id: uuid.UUID = None) -> str:
        """
        Deterministically returns a variant (e.g., 'control', 'variant_a') for a given experiment.
        Persists the assignment to track metrics later.
        """
        # Check if already assigned
        stmt = select(ProductExperiment).where(
            ProductExperiment.experiment_name == experiment_name,
            ProductExperiment.workspace_id == workspace_id,
            ProductExperiment.user_id == user_id
        )
        result = await db.execute(stmt)
        assignment = result.scalar_one_or_none()
        
        if assignment:
            return assignment.variant
            
        # Deterministic assignment based on ID hashing (50/50 split mock)
        target_id = str(user_id) if user_id else str(workspace_id)
        hash_val = int(hashlib.sha256(target_id.encode('utf-8')).hexdigest(), 16)
        variant = "variant_a" if hash_val % 2 == 0 else "control"
        
        new_assignment = ProductExperiment(
            experiment_name=experiment_name,
            workspace_id=workspace_id,
            user_id=user_id,
            variant=variant
        )
        db.add(new_assignment)
        await db.commit()
        
        return variant
