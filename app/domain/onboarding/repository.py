import uuid
from typing import List, Optional, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domain.onboarding.models import (
    WorkspaceProvisioning,
    OnboardingIntegrationConnection,
    ImportJob,
    ValidationResult,
    GoLiveAssessment,
    OperationalCapabilityMatrix,
    WorkspaceMaturity
)

class OnboardingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_provisioning(self, workspace_id: uuid.UUID) -> Optional[WorkspaceProvisioning]:
        result = await self.session.execute(
            select(WorkspaceProvisioning).where(WorkspaceProvisioning.workspace_id == workspace_id)
        )
        return result.scalars().first()

    async def get_integrations(self, workspace_id: uuid.UUID) -> List[OnboardingIntegrationConnection]:
        result = await self.session.execute(
            select(OnboardingIntegrationConnection).where(OnboardingIntegrationConnection.workspace_id == workspace_id)
        )
        return result.scalars().all()

    async def get_latest_golive(self, workspace_id: uuid.UUID) -> Optional[GoLiveAssessment]:
        result = await self.session.execute(
            select(GoLiveAssessment)
            .where(GoLiveAssessment.workspace_id == workspace_id)
            .order_by(GoLiveAssessment.evaluated_at.desc())
        )
        return result.scalars().first()

    async def get_capabilities(self, workspace_id: uuid.UUID) -> List[OperationalCapabilityMatrix]:
        result = await self.session.execute(
            select(OperationalCapabilityMatrix).where(OperationalCapabilityMatrix.workspace_id == workspace_id)
        )
        return result.scalars().all()

    async def save_entity(self, entity: Any) -> Any:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
