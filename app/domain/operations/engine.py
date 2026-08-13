import uuid
from typing import Dict, Any, Optional, List
from uuid import UUID

from app.domain.operations.schemas import (
    OperationalRequest, CreateActionRequest, ActionEvidenceDTO, TransitionActionStatusRequest
)
from app.domain.operations.models import Action, ActionStatus, ActionDependency
from app.domain.operations.repository import ActionRepository
from app.domain.operations.exceptions import ActionNotFoundError
from app.domain.approval.engine import ApprovalEngine
from app.domain.approval.schemas import SubmitApprovalRequest, ApprovalContext
from app.domain.action.engine import ActionEngine
from app.events.model.operations_events import (
    ActionCreatedEvent, ActionStatusChangedEvent, ActionDependencyAddedEvent
)

from app.domain.operations.planning.service import ActionPlanningService
from app.domain.operations.orchestration.engine import ActionOrchestrationEngine

class OperationsEngine:
    def __init__(
        self, 
        approval_engine: ApprovalEngine, 
        action_engine: ActionEngine,
        repository: ActionRepository = None,
        planning_service: ActionPlanningService = None,
        orchestration_engine: Optional[ActionOrchestrationEngine] = None,
        event_bus: Any = None
    ):
        self.approval_engine = approval_engine
        self.action_engine = action_engine
        self.repository = repository
        self.planning_service = planning_service
        self.orchestration_engine = orchestration_engine
        self.event_bus = event_bus

    async def evaluate_governance(self, workspace_id: UUID, action_id: UUID, correlation_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        The central orchestrator for Phase 3.4 Governance.
        Flow:
        1. Ensure Action is READY.
        2. Evaluate Approval Policies.
        3. If Approval Required -> Transition Action to PENDING_APPROVAL.
        4. If No Approval Required -> Transition Action to APPROVED.
        """
        if not self.repository:
            raise RuntimeError("OperationsEngine not initialized with a repository")
            
        # Reconstruct SubmitApprovalRequest for backwards compatibility with ApprovalEngine
        action = await self.repository.get_action(workspace_id, action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found")
            
        approval_req = SubmitApprovalRequest(
            action_id=action_id,
            action_version=action.version_number,
            context=ApprovalContext(
                action_type=action.action_type,
                target_system=action.target.get("target_system", "unknown"),
                risk_level=getattr(action, "priority", "NORMAL"),
                action_summary=f"Approval for {action.action_type}"
            ),
            requested_by=action.owner.get("id", "system"),
            correlation_id=correlation_id
        )
        
        needs_approval, approval = await self.approval_engine.evaluate_action(workspace_id, approval_req, self.repository)
        
        if needs_approval and approval:
            # Transition to PENDING_APPROVAL
            await self.transition_status(workspace_id, action_id, TransitionActionStatusRequest(
                target_status=ActionStatus.PENDING_APPROVAL,
                expected_revision_id=action.revision_id,
                reason="Governance policy matched, approval required."
            ))
            return {
                "status": "awaiting_approval",
                "approval_id": approval.id,
                "action_id": action_id,
                "message": "Action requires approval before execution."
            }
            
        # No approval required, transition to APPROVED
        await self.transition_status(workspace_id, action_id, TransitionActionStatusRequest(
            target_status=ActionStatus.APPROVED,
            expected_revision_id=action.revision_id,
            reason="Governance evaluation passed, no approval required."
        ))
        return {
            "status": "approved",
            "action_id": action_id,
            "message": "Action approved for execution."
        }

    async def process_approval_decision(self, approval_id: UUID, req: Any, authenticated_actor_id: str) -> Dict[str, Any]:
        """
        Handles an approval decision.
        Transitions the underlying Action to APPROVED or REJECTED.
        """
        approval = await self.approval_engine.process_decision(approval_id, req, authenticated_actor_id, self.repository)
        
        if approval.status == "approved":
            # Transition Action to APPROVED
            action = await self.repository.get_action(approval.workspace_id, approval.action_id)
            if action:
                await self.transition_status(approval.workspace_id, action.id, TransitionActionStatusRequest(
                    target_status=ActionStatus.APPROVED,
                    expected_revision_id=action.revision_id,
                    reason=f"Approved by {authenticated_actor_id}"
                ))
        elif approval.status == "rejected":
            action = await self.repository.get_action(approval.workspace_id, approval.action_id)
            if action:
                await self.transition_status(approval.workspace_id, action.id, TransitionActionStatusRequest(
                    target_status=ActionStatus.REJECTED,
                    expected_revision_id=action.revision_id,
                    reason=f"Rejected by {authenticated_actor_id}"
                ))
        
        # Ensure the atomic transaction boundary is committed
        await self.repository.save()
            
        return {
            "approval_id": approval.id,
            "status": approval.status
        }

    async def create_action(self, workspace_id: UUID, request: CreateActionRequest) -> Action:
        if not self.repository:
            raise RuntimeError("OperationsEngine not initialized with a repository")
            
        action = Action(
            workspace_id=workspace_id,
            action_type=request.action_type,
            priority=request.priority,
            target=request.target,
            owner=request.owner,
            source=request.source,
            evidence=[e.model_dump() for e in request.evidence],
            provenance=request.provenance.model_dump(),
            execution_metadata=request.execution_metadata,
            idempotency_key=request.idempotency_key,
            correlation_id=request.correlation_id,
            status=ActionStatus.DETECTED
        )
        
        # Do NOT add dependencies directly to avoid bypassing planning rules
        action = await self.repository.create_action(action)
        await self.repository.save()
        
        # Add dependencies properly using the planning service
        if self.planning_service:
            for dep_id in request.dependency_action_ids:
                await self.planning_service.add_dependency(workspace_id, action.id, dep_id)
        
        if self.event_bus:
            event = ActionCreatedEvent(
                workspace_id=workspace_id,
                action_id=action.id,
                action_type=action.action_type,
                status=action.status,
                priority=action.priority
            )
            await self.event_bus.publish(event)
            
            for dep_id in request.dependency_action_ids:
                dep_event = ActionDependencyAddedEvent(
                    workspace_id=workspace_id,
                    action_id=action.id,
                    depends_on_action_id=dep_id
                )
                await self.event_bus.publish(dep_event)
                
        return action

    async def transition_status(self, workspace_id: UUID, action_id: UUID, request: TransitionActionStatusRequest) -> Action:
        if not self.repository:
            raise RuntimeError("OperationsEngine not initialized with a repository")
            
        action = await self.repository.get_action(workspace_id, action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found")
            
        if request.expected_revision_id and action.revision_id != request.expected_revision_id:
            raise ValueError("Revision mismatch")
            
        old_status = action.status
        action.status = request.target_status
        action.advance_revision()
        await self.repository.save()
        
        if self.event_bus and old_status != action.status:
            event = ActionStatusChangedEvent(
                workspace_id=workspace_id,
                action_id=action.id,
                old_status=old_status,
                new_status=action.status,
                reason=request.reason
            )
            await self.event_bus.publish(event)
            
        return action

    async def add_evidence(self, workspace_id: UUID, action_id: UUID, evidence: ActionEvidenceDTO) -> Action:
        if not self.repository:
            raise RuntimeError("OperationsEngine not initialized with a repository")
            
        action = await self.repository.get_action(workspace_id, action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found")
            
        evidence_list = list(action.evidence)
        evidence_list.append(evidence.model_dump())
        action.evidence = evidence_list
        action.advance_revision()
        await self.repository.save()
        return action

    async def add_dependency(self, workspace_id: UUID, action_id: UUID, depends_on_action_id: UUID) -> Action:
        if not self.planning_service:
            raise RuntimeError("OperationsEngine not initialized with a planning service")
            
        await self.planning_service.add_dependency(workspace_id, action_id, depends_on_action_id)
        
        if self.event_bus:
            event = ActionDependencyAddedEvent(
                workspace_id=workspace_id,
                action_id=action_id,
                depends_on_action_id=depends_on_action_id
            )
            await self.event_bus.publish(event)
            
        return await self.repository.get_action(workspace_id, action_id)

    async def remove_dependency(self, workspace_id: UUID, action_id: UUID, depends_on_action_id: UUID) -> Action:
        if not self.planning_service:
            raise RuntimeError("OperationsEngine not initialized with a planning service")
            
        await self.planning_service.remove_dependency(workspace_id, action_id, depends_on_action_id)
        
        # Publish ActionDependencyRemovedEvent
        if self.event_bus:
            from app.events.model.operations_events import ActionDependencyRemovedEvent
            event = ActionDependencyRemovedEvent(
                workspace_id=workspace_id,
                action_id=action_id,
                depends_on_action_id=depends_on_action_id
            )
            await self.event_bus.publish(event)
            
        return await self.repository.get_action(workspace_id, action_id)

    async def get_blockers(self, workspace_id: UUID, action_id: UUID) -> List[UUID]:
        if not self.planning_service:
            raise RuntimeError("OperationsEngine not initialized with a planning service")
        readiness = await self.planning_service.evaluate_readiness(workspace_id, action_id)
        return readiness.blockers

    async def get_readiness(self, workspace_id: UUID, action_id: UUID):
        if not self.planning_service:
            raise RuntimeError("OperationsEngine not initialized with a planning service")
        return await self.planning_service.evaluate_readiness(workspace_id, action_id)


