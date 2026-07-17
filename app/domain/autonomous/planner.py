from typing import List, Tuple, Dict, Any
from abc import ABC, abstractmethod
import uuid

from app.domain.autonomous.models import OperationalOpportunity, ExecutionPlan, PlanStep, StepType


class BasePlanner(ABC):
    @abstractmethod
    def generate_plan(self, opportunity: OperationalOpportunity) -> Tuple[ExecutionPlan, List[PlanStep]]:
        """
        Deterministically maps an opportunity into an execution plan and its steps.
        """
        pass


class ReengagementPlanner(BasePlanner):
    """
    Example Planner for "REENGAGE_CUSTOMER" opportunity type.
    """
    def generate_plan(self, opportunity: OperationalOpportunity) -> Tuple[ExecutionPlan, List[PlanStep]]:
        plan = ExecutionPlan(
            workspace_id=opportunity.workspace_id,
            opportunity_id=opportunity.id,
            plan_version="1.0",
            idempotency_key=f"plan_{opportunity.id}_v1",
            mission_priority=1,
            success_criteria={"email_opened": True},
            failure_strategy="COMPENSATE",
            compensation_plan={
                "action": "CREATE_INTERNAL_TASK",
                "assignee": "SALES_TEAM",
                "notes": "Failed to re-engage autonomously, manual follow-up required."
            }
        )
        
        # Step 1: Send Re-engagement Email
        step1 = PlanStep(
            step_index=0,
            type=StepType.ACTION.value,
            idempotency_key=f"step_{opportunity.id}_0",
            inputs={
                "action_type": "SEND_EMAIL",
                "target_id": opportunity.source_reference_id, # e.g. customer ID
                "template": "REENGAGEMENT_V1"
            },
            retry_policy={"max_retries": 3, "backoff_ms": 1000}
        )
        
        # Step 2: Wait 24h for engagement
        step2 = PlanStep(
            step_index=1,
            type=StepType.WAIT.value,
            idempotency_key=f"step_{opportunity.id}_1",
            dependencies=[0],
            inputs={
                "duration_seconds": 86400
            }
        )
        
        # Step 3: Validate engagement (Check Open Rate/Reply)
        step3 = PlanStep(
            step_index=2,
            type=StepType.VALIDATION.value,
            idempotency_key=f"step_{opportunity.id}_2",
            dependencies=[1],
            inputs={
                "validation_type": "CHECK_EMAIL_ENGAGEMENT",
                "target_id": opportunity.source_reference_id
            }
        )
        
        return plan, [step1, step2, step3]


class PlannerRegistry:
    def __init__(self):
        self._planners: Dict[str, BasePlanner] = {
            "REENGAGE_CUSTOMER": ReengagementPlanner()
        }

    def get_planner(self, opportunity_type: str) -> BasePlanner:
        planner = self._planners.get(opportunity_type)
        if not planner:
            raise ValueError(f"No specialized planner registered for opportunity type: {opportunity_type}")
        return planner
