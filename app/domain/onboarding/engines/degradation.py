import uuid
from typing import List, Dict, Any

from app.domain.onboarding.repository import OnboardingRepository
from app.domain.onboarding.models import OperationalCapabilityMatrix

class GracefulDegradationEngine:
    """
    Manages the Operational Capability Matrix.
    Routes capabilities to 'Human Review' or 'Limited' instead of failing the workspace.
    """

    @classmethod
    async def evaluate_degradation(
        cls, 
        repo: OnboardingRepository, 
        workspace_id: uuid.UUID,
        integration_status: str
    ):
        """
        Example: If CRM integration drops, degrade 'Lead Assignment'.
        """
        if integration_status != "CONNECTED":
            # Degrade capabilities
            cap = OperationalCapabilityMatrix(
                workspace_id=workspace_id,
                capability_name="LEAD_ASSIGNMENT",
                status="HUMAN_REVIEW",
                reason="CRM Integration disconnected or unhealthy"
            )
            await repo.save_entity(cap)
