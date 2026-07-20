import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import Dict, Any, Optional

from app.domain.pilot.models import PilotDeployment, PilotPhase

logger = logging.getLogger("hunteros.pilot")

class PilotOnboardingEngine:
    """
    Manages the lifecycle of a Pilot Deployment, tracking progress from discovery to review.
    """

    @staticmethod
    async def initiate_pilot(db: AsyncSession, workspace_id: uuid.UUID, company_name: str, criteria: Dict[str, Any]) -> PilotDeployment:
        """
        Begins a new Pilot Deployment engagement.
        """
        pilot = PilotDeployment(
            workspace_id=workspace_id,
            company_name=company_name,
            phase=PilotPhase.discovery,
            success_criteria=criteria
        )
        db.add(pilot)
        await db.commit()
        await db.refresh(pilot)
        
        logger.info(f"Initiated pilot for {company_name} (Workspace: {workspace_id})")
        return pilot

    @staticmethod
    async def advance_phase(db: AsyncSession, pilot_id: uuid.UUID, new_phase: PilotPhase) -> Optional[PilotDeployment]:
        """
        Moves the pilot into the next deployment phase.
        """
        stmt = select(PilotDeployment).where(PilotDeployment.id == pilot_id)
        result = await db.execute(stmt)
        pilot = result.scalar_one_or_none()
        
        if not pilot:
            return None
            
        pilot.phase = new_phase
        await db.commit()
        
        logger.info(f"Pilot {pilot_id} advanced to phase {new_phase}")
        return pilot
