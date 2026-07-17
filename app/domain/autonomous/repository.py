from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.autonomous.models import OperationalOpportunity, ExecutionPlan, PlanStep, ExecutionJournal


class AutonomousRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Opportunities ---
    
    async def get_opportunity(self, opportunity_id: UUID) -> Optional[OperationalOpportunity]:
        stmt = select(OperationalOpportunity).where(OperationalOpportunity.id == opportunity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
        
    async def get_opportunities_by_workspace(self, workspace_id: UUID) -> List[OperationalOpportunity]:
        stmt = select(OperationalOpportunity).where(OperationalOpportunity.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save_opportunity(self, opportunity: OperationalOpportunity) -> OperationalOpportunity:
        self.session.add(opportunity)
        await self.session.commit()
        await self.session.refresh(opportunity)
        return opportunity

    # --- Execution Plans ---
    
    async def get_plan(self, plan_id: UUID) -> Optional[ExecutionPlan]:
        stmt = select(ExecutionPlan).where(ExecutionPlan.id == plan_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_plans_by_workspace(self, workspace_id: UUID) -> List[ExecutionPlan]:
        stmt = select(ExecutionPlan).where(ExecutionPlan.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    # --- Plan Steps ---
    
    async def get_steps_for_plan(self, plan_id: UUID) -> List[PlanStep]:
        stmt = select(PlanStep).where(PlanStep.plan_id == plan_id).order_by(PlanStep.step_index.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save_step(self, step: PlanStep) -> PlanStep:
        self.session.add(step)
        await self.session.commit()
        await self.session.refresh(step)
        return step

    # --- Execution Journal ---
    
    async def get_journal_entries(self, plan_id: UUID) -> List[ExecutionJournal]:
        stmt = select(ExecutionJournal).where(ExecutionJournal.plan_id == plan_id).order_by(ExecutionJournal.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_journal_entry(self, entry: ExecutionJournal) -> ExecutionJournal:
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry
