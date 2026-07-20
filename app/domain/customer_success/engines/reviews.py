import logging
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.customer_success.models import ExecutiveReview
from app.domain.roi.engines.calculator import ROICalculator

logger = logging.getLogger("hunteros.cs")

class ExecutiveReviewEngine:
    """
    Automates the generation of Quarterly Executive Business Reviews (EBRs).
    """

    @staticmethod
    async def generate_ebr(db: AsyncSession, workspace_id: uuid.UUID) -> ExecutiveReview:
        """
        Pulls current ROI and Friction data to generate a business review artifact.
        """
        # Fetch actual ROI calculations using the core domain
        roi_report = await ROICalculator.calculate_impact(db, workspace_id)
        
        review = ExecutiveReview(
            workspace_id=workspace_id,
            review_date=datetime.utcnow(),
            roi_snapshot_json=roi_report,
            next_steps_json=[
                {"recommendation": "Expand AI context to ERP data to improve recommendations by 15%."}
            ]
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)
        
        logger.info(f"Generated Executive Business Review for Workspace {workspace_id}")
        return review
