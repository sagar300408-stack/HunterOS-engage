import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.autonomous.models import ExecutionPlan, PlanStep, ExecutionJournal, PlanStatus, StepStatus, StepType
from app.domain.autonomous.repository import AutonomousRepository
from app.domain.autonomous.safety import SafetyEnforcer
from app.events.bus.event_bus import EventBus
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType


class MissionCoordinator:
    def __init__(self, session: AsyncSession, event_bus: EventBus):
        self.session = session
        self.repo = AutonomousRepository(session)
        self.event_bus = event_bus

    async def reconcile_plan(self, plan_id: uuid.UUID, triggering_event: str = "manual_reconciliation", metadata: dict = None) -> ExecutionPlan:
        """
        Idempotent function that evaluates the current state of a plan and its steps,
        progressing the state machine forward when possible.
        """
        if metadata is None:
            metadata = {}

        plan = await self.repo.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")

        # Terminal states shouldn't progress
        if plan.status in [PlanStatus.COMPLETED.value, PlanStatus.FAILED.value, PlanStatus.ROLLED_BACK.value, PlanStatus.CANCELLED.value]:
            return plan

        steps = await self.repo.get_steps_for_plan(plan_id)
        
        # If it's just PLANNED, mark it EXECUTING and journal it
        if plan.status == PlanStatus.PLANNED.value:
            old_status = plan.status
            plan.status = PlanStatus.EXECUTING.value
            plan = await self.repo.save_plan(plan)
            await self._record_journal(plan.id, None, triggering_event, old_status, plan.status, "Plan started", metadata)
            await self._publish_event(plan.workspace_id, "autonomous.plan.started", {"plan_id": str(plan.id)})

        all_completed = True
        plan_failed = False
        
        # Build map of step statuses
        step_status_map = {step.step_index: step.status for step in steps}

        for step in steps:
            if step.status == StepStatus.FAILED.value:
                plan_failed = True
                break
                
            if step.status in [StepStatus.PENDING.value]:
                all_completed = False
                
                # Check dependencies
                dependencies = step.dependencies or []
                deps_met = all(step_status_map.get(dep_idx) == StepStatus.SUCCESS.value for dep_idx in dependencies)
                if deps_met:
                    # Time to dispatch this step
                    await self._dispatch_step(plan, step, triggering_event)
                    # After dispatching one step, we break to allow async execution. 
                    # Reconcile will be called again when that step finishes.
                    return plan
                    
            elif step.status == StepStatus.EXECUTING.value:
                all_completed = False
                # If it's a WAIT step, check if it's done (mocking timer logic)
                if step.type == StepType.WAIT.value:
                    # In a real app, a scheduler would call reconcile_plan after the timeout.
                    # For testing, if we see a WAIT step executing, we can auto-complete it or rely on external test triggers.
                    pass
                
                # In general, if a step is EXECUTING, we wait for it to finish and callback via reconcile_plan.
                break

        if plan_failed:
            old_status = plan.status
            plan.status = PlanStatus.FAILED.value
            plan = await self.repo.save_plan(plan)
            await self._record_journal(plan.id, None, triggering_event, old_status, plan.status, "A step failed", metadata)
            await self._publish_event(plan.workspace_id, "autonomous.plan.failed", {"plan_id": str(plan.id)})
            # Here we would trigger compensation/rollback if strategy demands it

        elif all_completed:
            old_status = plan.status
            plan.status = PlanStatus.COMPLETED.value
            plan = await self.repo.save_plan(plan)
            await self._record_journal(plan.id, None, triggering_event, old_status, plan.status, "All steps completed successfully", metadata)
            await self._publish_event(plan.workspace_id, "autonomous.plan.completed", {"plan_id": str(plan.id)})
            
        return plan

    async def _dispatch_step(self, plan: ExecutionPlan, step: PlanStep, triggering_event: str):
        # 1. Evaluate Safety
        # Mocking workspace settings for demonstration
        workspace_settings = {"is_active": True, "enforce_business_hours": False} 
        is_safe, reason = SafetyEnforcer.evaluate_dispatch(step, workspace_settings)
        
        if not is_safe:
            # We can't dispatch. Fail the step.
            old_status = step.status
            step.status = StepStatus.FAILED.value
            step.outputs = {"error": "Safety check failed", "reason": reason}
            await self.repo.save_step(step)
            await self._record_journal(plan.id, step.id, triggering_event, old_status, step.status, f"Safety violation: {reason}", {})
            return

        # 2. Mark EXECUTING
        old_status = step.status
        step.status = StepStatus.EXECUTING.value
        await self.repo.save_step(step)
        await self._record_journal(plan.id, step.id, triggering_event, old_status, step.status, "Dispatched step", step.inputs)
        
        # 3. Actually dispatch to the underlying engines (ActionEngine, ApprovalEngine, Scheduler)
        # For this prototype, we simulate dispatch by publishing an internal event that the respective engine would listen to.
        # In a real integration, we might call OperationsEngine.submit(...) here.
        await self._publish_event(plan.workspace_id, "autonomous.step.dispatched", {
            "plan_id": str(plan.id),
            "step_id": str(step.id),
            "step_type": step.type,
            "inputs": step.inputs
        })
        
        # If testing/mocking, one might instantly resolve it. We'll leave it as EXECUTING for tests to resolve.

    async def _record_journal(self, plan_id: uuid.UUID, step_id: Optional[uuid.UUID], triggering_event: str, prev: str, new: str, reason: str, metadata: dict):
        journal = ExecutionJournal(
            plan_id=plan_id,
            step_id=step_id,
            triggering_event=triggering_event,
            previous_state=prev,
            new_state=new,
            reason=reason,
            metadata_json=metadata
        )
        await self.repo.add_journal_entry(journal)

    async def _publish_event(self, workspace_id: uuid.UUID, event_name: str, metadata: Dict[str, Any]) -> None:
        event = UniversalBaseEvent(
            workspace_id=workspace_id,
            category=EventCategory.AUTONOMOUS,
            event_name=event_name,
            correlation_id=None,
            metadata=metadata,
            actor_type=ActorType.SYSTEM,
            source_subsystem="mission_coordinator"
        )
        await self.event_bus.publish(event)
