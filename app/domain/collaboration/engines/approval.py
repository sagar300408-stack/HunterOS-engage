from typing import List, Optional
import uuid
from datetime import datetime, timezone
from sqlalchemy.future import select

from app.domain.collaboration.models import (
    CollaborationTask, 
    TaskApprovalChain, 
    ApprovalStatus,
    ActionableIntent,
    TaskStatus
)
from app.domain.collaboration.repository import CollaborationRepository

class HumanApprovalFramework:
    """
    Handles dynamic multi-level approval chains.
    """

    @classmethod
    async def attach_approval_chain(cls, repo: CollaborationRepository, task: CollaborationTask, intent: ActionableIntent):
        """
        Builds the chain based on intent type and context data.
        """
        deal_value = float(intent.context_data.get("deal_value", 0))
        
        chains = []
        
        if intent.intent_type == "approve_discount":
            if deal_value > 200000:
                chains.append(TaskApprovalChain(task_id=task.id, level=1, required_role="Sales Manager"))
                chains.append(TaskApprovalChain(task_id=task.id, level=2, required_role="Finance"))
                chains.append(TaskApprovalChain(task_id=task.id, level=3, required_role="Director"))
            elif deal_value > 25000:
                chains.append(TaskApprovalChain(task_id=task.id, level=1, required_role="Sales Manager"))
        
        elif intent.intent_type == "legal_agreement":
            chains.append(TaskApprovalChain(task_id=task.id, level=1, required_role="Legal"))
            chains.append(TaskApprovalChain(task_id=task.id, level=2, required_role="Director"))
            chains.append(TaskApprovalChain(task_id=task.id, level=3, required_role="CEO"))
        else:
            # Default single level
            chains.append(TaskApprovalChain(task_id=task.id, level=1, required_role="Manager"))
            
        repo.session.add_all(chains)
        await repo.session.commit()

    @classmethod
    async def process_approval(
        cls, 
        repo: CollaborationRepository, 
        task_id: uuid.UUID, 
        approver_id: uuid.UUID, 
        approve: bool
    ) -> CollaborationTask:
        """
        Approves the lowest pending level. If rejected, fails the task.
        If approved and more levels exist, moves to next. 
        If approved and last level, completes the task.
        """
        task = await repo.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
            
        pending_chains = sorted([c for c in task.approvals if c.status == ApprovalStatus.PENDING], key=lambda x: x.level)
        
        if not pending_chains:
            raise ValueError("No pending approvals for this task.")
            
        current_chain = pending_chains[0]
        
        if not approve:
            current_chain.status = ApprovalStatus.REJECTED
            current_chain.approver_id = approver_id
            current_chain.resolved_at = datetime.now(timezone.utc)
            task.status = TaskStatus.REJECTED
            task.resolved_at = datetime.now(timezone.utc)
        else:
            current_chain.status = ApprovalStatus.APPROVED
            current_chain.approver_id = approver_id
            current_chain.resolved_at = datetime.now(timezone.utc)
            
            # Check if there are more chains
            if len(pending_chains) == 1:
                # This was the last one
                task.status = TaskStatus.COMPLETED
                task.resolved_at = datetime.now(timezone.utc)
                
        await repo.session.commit()
        return task
