from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.approval.models import ApprovalPolicy, ApprovalRequest, ApprovalDecision


class ApprovalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_active_policies(self, workspace_id: UUID) -> List[ApprovalPolicy]:
        stmt = select(ApprovalPolicy).where(
            ApprovalPolicy.workspace_id == workspace_id,
            ApprovalPolicy.enabled == True
        ).order_by(ApprovalPolicy.priority.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
        
    async def get_policy(self, policy_id: UUID) -> Optional[ApprovalPolicy]:
        stmt = select(ApprovalPolicy).where(ApprovalPolicy.id == policy_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_policy(self, policy: ApprovalPolicy) -> ApprovalPolicy:
        self.session.add(policy)
        await self.session.commit()
        await self.session.refresh(policy)
        return policy

    async def save_request(self, req: ApprovalRequest) -> ApprovalRequest:
        self.session.add(req)
        await self.session.commit()
        await self.session.refresh(req)
        return req

    async def update_request(self, req: ApprovalRequest) -> ApprovalRequest:
        self.session.add(req)
        await self.session.commit()
        await self.session.refresh(req)
        return req

    async def get_request(self, req_id: UUID) -> Optional[ApprovalRequest]:
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == req_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_decision(self, decision: ApprovalDecision) -> ApprovalDecision:
        self.session.add(decision)
        await self.session.commit()
        await self.session.refresh(decision)
        return decision

    async def get_decisions_for_stage(self, request_id: UUID, stage_index: int) -> List[ApprovalDecision]:
        stmt = select(ApprovalDecision).where(
            ApprovalDecision.approval_request_id == request_id,
            ApprovalDecision.stage_index == stage_index
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
