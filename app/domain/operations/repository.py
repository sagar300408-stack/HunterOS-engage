import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.operations.models import Action, ActionDependency
from app.domain.operations.exceptions import ActionConflictError, ActionNotFoundError

class ActionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_action(self, workspace_id: uuid.UUID, action_id: uuid.UUID) -> Optional[Action]:
        stmt = (
            select(Action)
            .options(selectinload(Action.dependencies), selectinload(Action.dependent_on_me))
            .where(Action.workspace_id == workspace_id)
            .where(Action.id == action_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_idempotency_key(self, workspace_id: uuid.UUID, idempotency_key: str) -> Optional[Action]:
        stmt = (
            select(Action)
            .options(selectinload(Action.dependencies), selectinload(Action.dependent_on_me))
            .where(Action.workspace_id == workspace_id)
            .where(Action.idempotency_key == idempotency_key)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_actions(self, workspace_id: uuid.UUID, limit: int = 50, offset: int = 0) -> Sequence[Action]:
        stmt = (
            select(Action)
            .where(Action.workspace_id == workspace_id)
            .order_by(Action.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_action(self, action: Action) -> Action:
        if action.idempotency_key:
            existing = await self.get_by_idempotency_key(action.workspace_id, action.idempotency_key)
            if existing:
                if (
                    existing.action_type == action.action_type and
                    existing.priority == action.priority and
                    existing.target == action.target
                ):
                    return existing
                else:
                    raise ActionConflictError("Action with this idempotency key already exists with different properties.")
        self.session.add(action)
        return action
