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

class OperationsEngine:
    def __init__(
        self, 
        approval_engine: ApprovalEngine, 
        action_engine: ActionEngine,
        repository: ActionRepository = None,
        planning_service: ActionPlanningService = None,
        event_bus: Any = None
    ):
        self.approval_engine = approval_engine
        self.action_engine = action_engine
        self.repository = repository
        self.planning_service = planning_service
        self.event_bus = event_bus

    async def submit_request(self, workspace_id: UUID, req: OperationalRequest) -> Dict[str, Any]:
        """
        The central orchestrator for all operational requests.
        Flow:
        1. Parse Request
        2. Evaluate Approval Policies
        3. If Approval Required -> Submit to ApprovalEngine and Pause
        4. If No Approval Required -> Submit to ActionEngine directly
        """
        # Create a placeholder action ID for tracking
        action_id = uuid.uuid4()
        
        # Determine approval context
        context = req.approval_context or ApprovalContext(
            action_type=req.action_type,
            target_system=req.target_system
        )
        
        approval_req = SubmitApprovalRequest(
            action_id=action_id,
            context=context,
            requested_by=req.requested_by,
            correlation_id=req.correlation_id
        )
        
        needs_approval, approval = await self.approval_engine.evaluate_action(workspace_id, approval_req)
        
        if needs_approval and approval:
            # Paused for approval
            return {
                "status": "awaiting_approval",
                "approval_id": approval.id,
                "action_id": action_id,
                "message": "Action requires approval before execution."
            }
            
        # No approval required, execute immediately
        # We need to map the generated action_id somehow. Let's just submit the action.
        action_req = req.to_submit_action_request()
        action = await self.action_engine.submit_action(workspace_id, action_req)
        
        # Technically action.id will be newly generated in ActionEngine, which overrides our placeholder action_id.
        # This is fine for now, we return the actual action ID.
        return {
            "status": "executing",
            "action_id": action.id,
            "message": "Action submitted for execution."
        }

    async def process_approval_decision(self, approval_id: UUID, req: Any) -> Dict[str, Any]:
        """
        Handles an approval decision. If the approval completes successfully,
        this will forward the original request to the Action Engine.
        """
        approval = await self.approval_engine.process_decision(approval_id, req)
        
        if approval.status == "approved":
            # In a full system, we would serialize the original request and reconstruct it here.
            # For Milestone 9.3, we will simulate this by assuming the request can be reconstructed.
            # The ActionEngine would be invoked here.
            pass
            
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
