import logging
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.domain.pilot.models import PilotFeedback, FeedbackSeverity

logger = logging.getLogger("hunteros.pilot")

class PilotFeedbackEngine:
    """
    Ingests and classifies continuous feedback provided during a pilot deployment.
    """

    @staticmethod
    async def submit_feedback(
        db: AsyncSession, 
        pilot_id: uuid.UUID, 
        content: str, 
        severity: FeedbackSeverity, 
        business_impact: str,
        user_id: uuid.UUID = None
    ) -> PilotFeedback:
        """
        Captures feedback and tracks business impact to ensure pilot blockers are resolved.
        """
        feedback = PilotFeedback(
            pilot_id=pilot_id,
            user_id=user_id,
            content=content,
            severity=severity,
            business_impact=business_impact
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        
        if severity in (FeedbackSeverity.high, FeedbackSeverity.critical):
            logger.warning(f"CRITICAL Feedback received for pilot {pilot_id}: {business_impact}")
            # Could trigger PagerDuty or internal Slack alerts here.
            
        return feedback
