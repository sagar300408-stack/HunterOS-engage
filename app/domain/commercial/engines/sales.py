import logging
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.domain.commercial.models import SalesPipelineLead, PipelineStage

logger = logging.getLogger("hunteros.commercial")


class SalesEngine:
    """
    Tracks the B2B sales pipeline from first lead to closed commercial customer.
    """

    @staticmethod
    async def create_lead(
        db: AsyncSession,
        company_name: str,
        contact_name: str = None,
        estimated_arr: float = None,
    ) -> SalesPipelineLead:
        """
        Registers a new sales lead at the top of the pipeline.
        """
        lead = SalesPipelineLead(
            company_name=company_name,
            contact_name=contact_name,
            stage=PipelineStage.lead,
            estimated_arr_usd=estimated_arr,
            win_probability=0.05,
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        logger.info(f"New lead created: {company_name}")
        return lead

    @staticmethod
    async def advance_stage(
        db: AsyncSession,
        lead_id: uuid.UUID,
        new_stage: PipelineStage,
        win_probability: float = None,
        note: str = None
    ) -> SalesPipelineLead:
        """
        Advances a lead to the next pipeline stage, updating probability and notes.
        """
        stmt = select(SalesPipelineLead).where(SalesPipelineLead.id == lead_id)
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        lead.stage = new_stage
        lead.stage_updated_at = datetime.utcnow()

        if win_probability is not None:
            lead.win_probability = win_probability

        if note:
            lead.notes = list(lead.notes or []) + [{"timestamp": datetime.utcnow().isoformat(), "note": note}]

        await db.commit()
        logger.info(f"Lead {lead.company_name} advanced to stage {new_stage}")
        return lead

    @staticmethod
    async def get_pipeline_summary(db: AsyncSession) -> dict:
        """
        Returns a rollup of pipeline value by stage for leadership dashboards.
        """
        stmt = (
            select(SalesPipelineLead.stage, func.count(SalesPipelineLead.id), func.sum(SalesPipelineLead.estimated_arr_usd))
            .group_by(SalesPipelineLead.stage)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return {
            "pipeline": [
                {"stage": row[0], "count": row[1], "total_estimated_arr": row[2] or 0}
                for row in rows
            ]
        }
