import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.domain.collaboration.models import (
    CollaborationTask,
    ActionableIntent,
    AutonomyPolicy,
    DecisionAuditLog,
    DecisionExplanation,
    TaskApprovalChain,
    LearningRule,
    TaskFeedback
)

class CollaborationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_intent(self, intent: ActionableIntent) -> ActionableIntent:
        self.session.add(intent)
        await self.session.commit()
        await self.session.refresh(intent)
        return intent

    async def create_task(self, task: CollaborationTask) -> CollaborationTask:
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task
    
    async def get_task_by_id(self, task_id: uuid.UUID) -> Optional[CollaborationTask]:
        result = await self.session.execute(
            select(CollaborationTask)
            .options(
                selectinload(CollaborationTask.intent),
                selectinload(CollaborationTask.audit_log).selectinload(DecisionAuditLog.explanation),
                selectinload(CollaborationTask.approvals)
            )
            .where(CollaborationTask.id == task_id)
        )
        return result.scalars().first()

    async def list_tasks(self, workspace_id: uuid.UUID, limit: int = 50) -> List[CollaborationTask]:
        result = await self.session.execute(
            select(CollaborationTask)
            .options(
                selectinload(CollaborationTask.intent),
                selectinload(CollaborationTask.audit_log).selectinload(DecisionAuditLog.explanation),
            )
            .where(CollaborationTask.workspace_id == workspace_id)
            .order_by(CollaborationTask.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_policy(self, workspace_id: uuid.UUID, intent_type: str) -> Optional[AutonomyPolicy]:
        result = await self.session.execute(
            select(AutonomyPolicy)
            .where(
                AutonomyPolicy.workspace_id == workspace_id,
                AutonomyPolicy.intent_type == intent_type
            )
        )
        return result.scalars().first()

    async def save_audit_log(self, audit: DecisionAuditLog) -> DecisionAuditLog:
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(audit)
        return audit

    async def get_learning_rules(self, workspace_id: uuid.UUID) -> List[LearningRule]:
        result = await self.session.execute(
            select(LearningRule)
            .where(LearningRule.workspace_id == workspace_id)
            .order_by(LearningRule.created_at.desc())
        )
        return result.scalars().all()

    async def save_feedback(self, feedback: TaskFeedback) -> TaskFeedback:
        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)
        return feedback
