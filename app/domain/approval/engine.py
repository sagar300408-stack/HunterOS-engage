from typing import Optional, List, Tuple
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

    async def evaluate_action(self, workspace_id: UUID, req: SubmitApprovalRequest) -> Tuple[bool, Optional[ApprovalRequest]]:
        """
        Evaluates an action against policies.
        Returns (needs_approval, approval_request).
        If needs_approval is False, the action can proceed immediately.
        """
        policies = await self.repo.get_all_active_policies(workspace_id)
        
        context_data = {
            "action_type": req.context.action_type,
            "target_system": req.context.target_system,
            "risk": req.context.risk_level,
            "impact": req.context.expected_impact,
            **req.context.business_context
        }
        
        matching_policy = None
        for policy in policies:
            if PolicyEvaluator.evaluate(policy, context_data):
                matching_policy = policy
                break
                
        if not matching_policy:
            return False, None
            
        # Create Approval Request
        approval_req = ApprovalRequest(
            workspace_id=workspace_id,
            action_id=req.action_id,
            policy_id=matching_policy.id,
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

    async def process_decision(self, approval_id: UUID, req: MakeDecisionRequest) -> ApprovalRequest:
        approval_req = await self.repo.get_request(approval_id)
        if not approval_req:
            raise ValueError(f"Approval {approval_id} not found.")
            
        if approval_req.status != ApprovalStatus.UNDER_REVIEW.value:
            raise ValueError(f"Approval is in {approval_req.status} state, cannot process decision.")
            
        policy = await self.repo.get_policy(approval_req.policy_id)
        if not policy:
            raise ValueError("Policy not found.")
            
        if approval_req.time_to_first_review_ms is None:
            approval_req.time_to_first_review_ms = int((datetime.now(timezone.utc) - approval_req.requested_at).total_seconds() * 1000)
            
        decision = ApprovalDecision(
            approval_request_id=approval_req.id,
            stage_index=approval_req.current_stage_index,
            approver_id=req.approver_id,
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
