from typing import Optional, List, Tuple, Any
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.approval.models import ApprovalRequest, ApprovalStatus, ApprovalDecision, ApprovalPolicy, ApprovalStageType
from app.domain.approval.schemas import SubmitApprovalRequest, MakeDecisionRequest
from app.domain.approval.repository import ApprovalRepository
from app.domain.approval.evaluator import PolicyEvaluator
from app.events.bus.event_bus import EventBus
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType


class ApprovalEngine:
    def __init__(self, session: AsyncSession, event_bus: EventBus):
        self.session = session
        self.repo = ApprovalRepository(session)
        self.event_bus = event_bus

    async def evaluate_action(self, workspace_id: UUID, req: SubmitApprovalRequest, action_repo: Any) -> Tuple[bool, Optional[ApprovalRequest]]:
        """
        Evaluates an action against policies.
        Returns (needs_approval, approval_request).
        If needs_approval is False, the action can proceed immediately.
        """
        action = await action_repo.get_action(workspace_id, req.action_id)
        if not action:
            raise ValueError(f"Action {req.action_id} not found in workspace {workspace_id}")

        if action.status not in ("READY", "PLANNED"):
            raise ValueError(f"Cannot evaluate governance for action in state {action.status}")

        policies = await self.repo.get_all_active_policies(workspace_id)
        
        context_data = {
            "action_type": req.context.action_type,
            "target_system": req.context.target_system,
            "risk": req.context.risk_level,
            "impact": req.context.expected_impact,
            **req.context.business_context
        }
        
        eval_result = PolicyEvaluator.evaluate_policies(policies, action, context_data)
                
        if not eval_result.approval_required:
            return False, None
            
        # Create Approval Request
        approval_req = ApprovalRequest(
            workspace_id=workspace_id,
            action_id=req.action_id,
            policy_id=eval_result.policy_id,
            correlation_id=req.correlation_id,
            status=ApprovalStatus.PENDING.value,
            current_stage_index=0,
            requested_by=req.requested_by,
            action_summary=req.context.action_summary,
            business_context=req.context.business_context,
            risk_level=req.context.risk_level,
            expected_impact=req.context.expected_impact,
            recommendation_id=req.context.recommendation_id,
            insight_id=req.context.insight_id,
            health_id=req.context.health_id
        )
        
        approval_req = await self.repo.save_request(approval_req)
        await self._publish_event(approval_req, "approval.requested")
        
        # Move to first stage
        approval_req.status = ApprovalStatus.UNDER_REVIEW.value
        approval_req = await self.repo.update_request(approval_req)
        await self._publish_event(approval_req, "approval.stage_started")
        
        return True, approval_req

    async def process_decision(self, approval_id: UUID, req: MakeDecisionRequest, authenticated_actor_id: str, action_repo: Any = None) -> ApprovalRequest:
        approval_req = await self.repo.get_request(approval_id)
        if not approval_req:
            raise ValueError(f"Approval {approval_id} not found.")
            
        if approval_req.status != ApprovalStatus.UNDER_REVIEW.value:
            raise ValueError(f"Approval is in {approval_req.status} state, cannot process decision.")
            
        # Authorization validation
        # The approver identity MUST be derived from the authenticated execution context.
        # If the client provided an approver_id, we validate that it matches the authenticated context.
        if req.approver_id and req.approver_id != authenticated_actor_id:
            raise PermissionError(f"Authenticated actor {authenticated_actor_id} is not authorized to act as {req.approver_id}")
            
        # Segregation of duties: The requester cannot approve their own request if policy prohibits it.
        # For V1, we simply record it. If there was a strict policy check, it would happen here.
        if approval_req.requested_by == authenticated_actor_id:
            # Note: A real strict policy check could be added here if defined in ApprovalPolicy
            pass

        policy = await self.repo.get_policy(approval_req.policy_id)
        if not policy:
            raise ValueError("Policy not found.")
            
        # Stage validation - check if the actor is in the authorized approvers list for the current stage
        stage_config = policy.stages[approval_req.current_stage_index]
        allowed_approvers = stage_config.get("approver_ids", [])
        if allowed_approvers and authenticated_actor_id not in allowed_approvers:
             raise PermissionError(f"Actor {authenticated_actor_id} is not authorized to approve stage {approval_req.current_stage_index}")

        if approval_req.time_to_first_review_ms is None:
            approval_req.time_to_first_review_ms = int((datetime.now(timezone.utc) - approval_req.requested_at).total_seconds() * 1000)
            
        decision = ApprovalDecision(
            approval_request_id=approval_req.id,
            stage_index=approval_req.current_stage_index,
            approver_id=authenticated_actor_id,
            delegated_from_id=req.delegated_from_id,
            decision=req.decision,
            comments=req.comments
        )
        await self.repo.save_decision(decision)
        
        if req.decision == "REJECTED":
            approval_req.status = ApprovalStatus.REJECTED.value
            approval_req.time_to_final_approval_ms = int((datetime.now(timezone.utc) - approval_req.requested_at).total_seconds() * 1000)
            approval_req = await self.repo.update_request(approval_req)
            await self._publish_event(approval_req, "approval.rejected")
            return approval_req
            
        # Check if stage is complete
        stage_config = policy.stages[approval_req.current_stage_index]
        decisions = await self.repo.get_decisions_for_stage(approval_req.id, approval_req.current_stage_index)
        
        approved_count = sum(1 for d in decisions if d.decision == "APPROVED")
        required_count = stage_config.get("required_count", 1)
        
        if approved_count >= required_count:
            await self._publish_event(approval_req, "approval.stage_completed")
            
            # Next stage
            if approval_req.current_stage_index + 1 < len(policy.stages):
                approval_req.current_stage_index += 1
                approval_req = await self.repo.update_request(approval_req)
                await self._publish_event(approval_req, "approval.stage_started")
            else:
                approval_req.status = ApprovalStatus.APPROVED.value
                approval_req.time_to_final_approval_ms = int((datetime.now(timezone.utc) - approval_req.requested_at).total_seconds() * 1000)
                approval_req = await self.repo.update_request(approval_req)
                await self._publish_event(approval_req, "approval.approved")
                
        return approval_req

    async def _publish_event(self, req: ApprovalRequest, event_name: str) -> None:
        event = UniversalBaseEvent(
            workspace_id=req.workspace_id,
            category=EventCategory.APPROVAL,
            event_name=event_name,
            correlation_id=req.correlation_id,
            metadata={
                "approval_id": str(req.id),
                "action_id": str(req.action_id),
                "status": req.status,
                "current_stage": req.current_stage_index
            },
            actor_type=ActorType.SYSTEM,
            source_subsystem="approval_engine"
        )
        await self.event_bus.publish(event)
