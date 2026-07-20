import uuid
from typing import Tuple, List, Optional
from app.domain.collaboration.models import ActionableIntent, AutonomyLevel, AutonomyPolicy
from app.domain.collaboration.repository import CollaborationRepository

class AdaptiveAutonomyEngine:
    """
    Looks up the workspace-specific autonomy policy for the given intent type.
    """

    @classmethod
    async def evaluate(
        cls, 
        repo: CollaborationRepository, 
        workspace_id: uuid.UUID, 
        intent_type: str
    ) -> Tuple[AutonomyLevel, int, List[str]]:
        """
        Returns (AutonomyLevel, policy_version, list_of_factors).
        """
        factors = []
        policy = await repo.get_policy(workspace_id, intent_type)
        
        if policy:
            factors.append(f"Workspace Policy found: {policy.default_level.value} (v{policy.version})")
            return policy.default_level, policy.version, factors
            
        factors.append("No specific Workspace Policy found. Defaulting to HUMAN_REVIEW.")
        return AutonomyLevel.HUMAN_REVIEW, 1, factors
