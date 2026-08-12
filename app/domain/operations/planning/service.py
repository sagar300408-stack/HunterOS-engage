import uuid
import hashlib
from typing import List

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.domain.operations.models import Action, ActionDependency, ActionStatus
from app.domain.operations.repository import ActionRepository
from app.domain.operations.exceptions import (
    ActionNotFoundError,
    DependencyCycleError,
    WorkspaceIsolationError,
    InvalidDependencyError
)
from app.domain.operations.schemas import ActionReadiness
from app.domain.operations.planning.policy import DependencySatisfactionPolicy
from app.utils.clock import SystemClock


class ActionPlanningService:
    def __init__(self, session: AsyncSession, repository: ActionRepository):
        self.session = session
        self.repository = repository

    async def _acquire_workspace_lock(self, workspace_id: uuid.UUID) -> None:
        """
        Acquires a transaction-level advisory lock specific to the workspace.
        This completely serializes concurrent graph mutations for a given workspace,
        preventing concurrent cycle creation races.
        """
        # Hash UUID to a 64-bit integer
        lock_id = int(hashlib.md5(workspace_id.bytes).hexdigest()[:16], 16)
        # PostgreSQL advisory lock IDs are signed 64-bit integers.
        lock_id = lock_id - 2**63  # Shift to signed range
        
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)").bindparams(lock_id=lock_id)
        )

    async def _check_cycle(self, action_id: uuid.UUID, depends_on_action_id: uuid.UUID) -> bool:
        """
        Performs a full recursive DFS in PostgreSQL to verify adding 
        (action_id -> depends_on_action_id) would not form a cycle.
        Returns True if a cycle would be formed.
        """
        query = text("""
            WITH RECURSIVE traverse AS (
                SELECT depends_on_action_id
                FROM action_dependencies
                WHERE action_id = :target_id
                
                UNION
                
                SELECT ad.depends_on_action_id
                FROM action_dependencies ad
                INNER JOIN traverse t ON t.depends_on_action_id = ad.action_id
            )
            SELECT 1 FROM traverse WHERE depends_on_action_id = :start_id LIMIT 1;
        """)
        result = await self.session.execute(
            query.bindparams(target_id=depends_on_action_id, start_id=action_id)
        )
        return result.scalar() is not None

    async def add_dependency(self, workspace_id: uuid.UUID, action_id: uuid.UUID, depends_on_action_id: uuid.UUID) -> None:
        """
        Adds a dependency strictly within the application service transaction boundary.
        """
        await self._acquire_workspace_lock(workspace_id)
        
        action = await self.repository.get_action_basics(action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found")
        
        depends_on_action = await self.repository.get_action_basics(depends_on_action_id)
        if not depends_on_action:
            raise ActionNotFoundError(f"Prerequisite Action {depends_on_action_id} not found")
            
        if action.workspace_id != workspace_id or depends_on_action.workspace_id != workspace_id:
            raise WorkspaceIsolationError("Cross-workspace dependency linking is strictly prohibited.")
            
        allowed_states = {ActionStatus.DETECTED, ActionStatus.PLANNED, ActionStatus.READY}
        if action.status not in allowed_states:
            raise InvalidDependencyError(f"Cannot mutate dependencies of action in status {action.status}")
            
        if await self._check_cycle(action_id, depends_on_action_id):
            raise DependencyCycleError(f"Dependency {action_id} -> {depends_on_action_id} would create a cycle.")
            
        new_dep = ActionDependency(action_id=action_id, depends_on_action_id=depends_on_action_id)
        self.session.add(new_dep)
        
        try:
            await self.session.flush()
        except IntegrityError:
            # Handle duplicate gracefully (idempotent)
            await self.session.rollback()
            return
            
        await self.repository.save()
        
    async def remove_dependency(self, workspace_id: uuid.UUID, action_id: uuid.UUID, depends_on_action_id: uuid.UUID) -> None:
        await self._acquire_workspace_lock(workspace_id)
        
        action = await self.repository.get_action_basics(action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found")
            
        allowed_states = {ActionStatus.DETECTED, ActionStatus.PLANNED, ActionStatus.READY}
        if action.status not in allowed_states:
            raise InvalidDependencyError(f"Cannot mutate dependencies of action in status {action.status}")
            
        # Delete the dependency
        await self.session.execute(
            text("DELETE FROM action_dependencies WHERE action_id = :a_id AND depends_on_action_id = :d_id")
            .bindparams(a_id=action_id, d_id=depends_on_action_id)
        )
        await self.repository.save()

    async def evaluate_readiness(self, workspace_id: uuid.UUID, action_id: uuid.UUID) -> ActionReadiness:
        # We need the full action with dependencies to evaluate readiness.
        action = await self.repository.get_action(workspace_id, action_id)
        if not action:
            raise ActionNotFoundError(f"Action {action_id} not found")
            
        # Need to query the statuses of all prerequisites
        dep_ids = [dep.depends_on_action_id for dep in action.dependencies]
        
        blockers = []
        satisfied = []
        
        if dep_ids:
            # Query all prerequisite actions
            stmt = select(Action.id, Action.status).where(Action.id.in_(dep_ids))
            result = await self.session.execute(stmt)
            prereq_statuses = {row.id: row.status for row in result.all()}
            
            for d_id in dep_ids:
                status = prereq_statuses.get(d_id)
                if status and DependencySatisfactionPolicy.is_satisfied(status):
                    satisfied.append(d_id)
                else:
                    blockers.append(d_id)
                    
        state = "READY" if not blockers else "BLOCKED"
        
        return ActionReadiness(
            action_id=action_id,
            state=state,
            blockers=blockers,
            satisfied_dependencies=satisfied,
            action_version=action.version_number,
            evaluated_at=SystemClock.now().isoformat()
        )
