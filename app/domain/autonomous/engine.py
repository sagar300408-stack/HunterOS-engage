import uuid
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.autonomous.models import OperationalOpportunity, ExecutionPlan, PlanStatus
from app.domain.autonomous.repository import AutonomousRepository
from app.domain.autonomous.planner import PlannerRegistry
from app.domain.autonomous.coordinator import MissionCoordinator
from app.events.bus.event_bus import EventBus


class AutonomousOperationsEngine:
    def __init__(self, session: AsyncSession, event_bus: EventBus):
        self.session = session
        self.repo = AutonomousRepository(session)
        self.event_bus = event_bus
        self.planner_registry = PlannerRegistry()
        self.coordinator = MissionCoordinator(session, event_bus)

    async def list_opportunities(self, workspace_id: uuid.UUID) -> List[OperationalOpportunity]:
        return await self.repo.get_opportunities_by_workspace(workspace_id)

    async def list_plans(self, workspace_id: uuid.UUID) -> List[ExecutionPlan]:
        return await self.repo.get_plans_by_workspace(workspace_id)

    async def get_plan(self, plan_id: uuid.UUID) -> Optional[ExecutionPlan]:
        return await self.repo.get_plan(plan_id)

    async def create_opportunity(self, opportunity: OperationalOpportunity) -> OperationalOpportunity:
        """
        Creates an opportunity and automatically plans it.
        """
        opportunity = await self.repo.save_opportunity(opportunity)
        await self._plan_opportunity(opportunity)
        return opportunity

    async def _plan_opportunity(self, opportunity: OperationalOpportunity) -> ExecutionPlan:
        planner = self.planner_registry.get_planner(opportunity.opportunity_type)
        plan, steps = planner.generate_plan(opportunity)
        
        # Save plan
        plan = await self.repo.save_plan(plan)
        
        # Save steps
        for step in steps:
            step.plan_id = plan.id
            await self.repo.save_step(step)

        # Update opportunity status
        opportunity.status = "PLANNED"
        await self.repo.save_opportunity(opportunity)

        # We do NOT start executing automatically here. The API or a scheduler invokes execution.
        return plan

    async def execute_plan(self, plan_id: uuid.UUID, idempotency_key: str = None) -> ExecutionPlan:
        """
        Manually (or via API) request execution of a plan. 
        Usually this just triggers reconciliation.
        """
        plan = await self.repo.get_plan(plan_id)
        if not plan:
            raise ValueError("Plan not found")
            
        if idempotency_key and plan.idempotency_key == idempotency_key:
            return plan # Already processed/processing

        return await self.coordinator.reconcile_plan(plan_id, triggering_event="api.execute_plan")

    async def cancel_plan(self, plan_id: uuid.UUID, reason: str) -> ExecutionPlan:
        plan = await self.repo.get_plan(plan_id)
        if not plan:
            raise ValueError("Plan not found")

        if plan.status not in [PlanStatus.COMPLETED.value, PlanStatus.FAILED.value, PlanStatus.ROLLED_BACK.value, PlanStatus.CANCELLED.value]:
            old_status = plan.status
            plan.status = PlanStatus.CANCELLED.value
            plan = await self.repo.save_plan(plan)
            
            await self.coordinator._record_journal(
                plan.id, None, "api.cancel_plan", old_status, plan.status, f"Cancelled by user/system: {reason}", {}
            )
            
            await self.coordinator._publish_event(plan.workspace_id, "autonomous.plan.cancelled", {"plan_id": str(plan.id), "reason": reason})
            
        return plan
