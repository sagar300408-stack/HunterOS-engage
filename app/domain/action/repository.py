from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.action.models import ActionExecution


class ActionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, action_id: UUID) -> Optional[ActionExecution]:
        stmt = select(ActionExecution).where(ActionExecution.id == action_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, workspace_id: UUID, idempotency_key: str) -> Optional[ActionExecution]:
        stmt = select(ActionExecution).where(
            ActionExecution.workspace_id == workspace_id,
            ActionExecution.idempotency_key == idempotency_key
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_action(self, action: ActionExecution) -> ActionExecution:
        try:
            self.session.add(action)
            await self.session.commit()
            await self.session.refresh(action)
            return action
        except IntegrityError:
            await self.session.rollback()
            raise ValueError(f"Action with idempotency key '{action.idempotency_key}' already exists in this workspace.")

    async def update_action(self, action: ActionExecution) -> ActionExecution:
        self.session.add(action)
        await self.session.commit()
        await self.session.refresh(action)
        return action
