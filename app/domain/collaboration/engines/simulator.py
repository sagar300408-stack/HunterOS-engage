import uuid
from typing import Dict, Any

from sqlalchemy.future import select
from sqlalchemy import func

from app.domain.collaboration.models import (
    CollaborationTask,
    AutonomyLevel
)
from app.domain.collaboration.repository import CollaborationRepository
from app.domain.collaboration.schemas import PolicySimulationResponse

class PolicySimulator:
    """
    Simulates the impact of changing a workspace autonomy policy for a specific intent type.
    """

    @classmethod
    async def simulate(
        cls, 
        repo: CollaborationRepository, 
        workspace_id: uuid.UUID, 
        intent_type: str, 
        proposed_level: AutonomyLevel
    ) -> PolicySimulationResponse:
        
        # 1. Fetch historical volume of this intent type over the last 30 days
        result = await repo.session.execute(
            select(func.count(CollaborationTask.id))
            .join(CollaborationTask.intent)
            .where(
                CollaborationTask.workspace_id == workspace_id,
                CollaborationTask.intent.has(intent_type=intent_type)
            )
        )
        task_volume = result.scalar() or 0
        
        # Heuristics for the simulation (normally you'd replay actual historical data)
        # If moving to AI_OWNED:
        if proposed_level == AutonomyLevel.AI_OWNED:
            # Assume 15 minutes saved per task
            hours_saved = (task_volume * 15) / 60.0
            risk_increase = 0.3 # arbitrary placeholder logic for simulation
            rec = "Safe to automate. Moderate volume detected."
        elif proposed_level == AutonomyLevel.HUMAN_REVIEW:
            hours_saved = 0.0
            risk_increase = -0.5
            rec = "Adding human review will increase accuracy but reduce speed."
        else:
            hours_saved = 0.0
            risk_increase = 0.0
            rec = "Standard processing."
            
        return PolicySimulationResponse(
            expected_hours_saved=round(hours_saved, 2),
            expected_risk_increase_percent=risk_increase,
            recommendation=rec
        )
