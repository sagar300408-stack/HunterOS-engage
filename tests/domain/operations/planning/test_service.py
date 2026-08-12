import uuid
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.exc import IntegrityError
from app.domain.operations.planning.service import ActionPlanningService
from app.domain.operations.models import Action, ActionStatus
from app.domain.operations.exceptions import (
    DependencyCycleError,
    WorkspaceIsolationError,
    InvalidDependencyError
)


class MockSessionWithLock(AsyncMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace_locks = {}
        self.execution_log = []
        self.cycle_found = False

    async def execute(self, query, *args, **kwargs):
        sql = str(query)
        if "pg_advisory_xact_lock" in sql:
            # Simple lock simulation per hash
            params = kwargs.get("parameters", {}) or query.compile().params
            # Extract lock_id if available, otherwise just use a global lock for mock simplicity
            lock_id = params.get("lock_id", "default")
            if lock_id not in self.workspace_locks:
                self.workspace_locks[lock_id] = asyncio.Lock()
            
            await self.workspace_locks[lock_id].acquire()
            self.execution_log.append(("lock_acquired", lock_id))
            
            mock_result = AsyncMock()
            return mock_result
            
        elif "WITH RECURSIVE" in sql:
            # Simulate slight delay to allow race condition if lock didn't exist
            await asyncio.sleep(0.01)
            self.execution_log.append("cycle_check")
            
            mock_result = MagicMock()
            if self.cycle_found:
                mock_result.scalar.return_value = 1
            else:
                mock_result.scalar.return_value = None
            return mock_result
            
        elif "DELETE FROM action_dependencies" in sql:
            self.execution_log.append("delete_dependency")
            return AsyncMock()
            
        return AsyncMock()

    def add(self, instance):
        self.execution_log.append("add")

    async def commit(self):
        self.execution_log.append("commit")
        # Release all acquired locks
        for lock in self.workspace_locks.values():
            if lock.locked():
                lock.release()

    async def flush(self):
        self.execution_log.append("flush")

    async def rollback(self):
        self.execution_log.append("rollback")
        for lock in self.workspace_locks.values():
            if lock.locked():
                lock.release()

@pytest.fixture
def mock_repository():
    repo = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_add_dependency_success(mock_repository):
    session = MockSessionWithLock()
    service = ActionPlanningService(session, mock_repository)
    
    workspace_id = uuid.uuid4()
    action_id = uuid.uuid4()
    depends_on_id = uuid.uuid4()
    
    a1 = Action(id=action_id, workspace_id=workspace_id, status=ActionStatus.PLANNED)
    a2 = Action(id=depends_on_id, workspace_id=workspace_id, status=ActionStatus.PLANNED)
    
    mock_repository.get_action_basics.side_effect = [a1, a2]
    
    await service.add_dependency(workspace_id, action_id, depends_on_id)
    
    assert "cycle_check" in session.execution_log
    assert "flush" in session.execution_log
    mock_repository.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_workspace_isolation(mock_repository):
    session = MockSessionWithLock()
    service = ActionPlanningService(session, mock_repository)
    
    workspace_id = uuid.uuid4()
    other_workspace_id = uuid.uuid4()
    
    a1 = Action(id=uuid.uuid4(), workspace_id=workspace_id, status=ActionStatus.PLANNED)
    a2 = Action(id=uuid.uuid4(), workspace_id=other_workspace_id, status=ActionStatus.PLANNED)
    
    mock_repository.get_action_basics.side_effect = [a1, a2]
    
    with pytest.raises(WorkspaceIsolationError):
        await service.add_dependency(workspace_id, a1.id, a2.id)


@pytest.mark.asyncio
async def test_lifecycle_validation(mock_repository):
    session = MockSessionWithLock()
    service = ActionPlanningService(session, mock_repository)
    
    workspace_id = uuid.uuid4()
    
    a1 = Action(id=uuid.uuid4(), workspace_id=workspace_id, status=ActionStatus.EXECUTING)
    a2 = Action(id=uuid.uuid4(), workspace_id=workspace_id, status=ActionStatus.PLANNED)
    
    mock_repository.get_action_basics.side_effect = [a1, a2]
    
    with pytest.raises(InvalidDependencyError):
        await service.add_dependency(workspace_id, a1.id, a2.id)


@pytest.mark.asyncio
async def test_cycle_detection(mock_repository):
    session = MockSessionWithLock()
    session.cycle_found = True
    service = ActionPlanningService(session, mock_repository)
    
    workspace_id = uuid.uuid4()
    a1 = Action(id=uuid.uuid4(), workspace_id=workspace_id, status=ActionStatus.PLANNED)
    a2 = Action(id=uuid.uuid4(), workspace_id=workspace_id, status=ActionStatus.PLANNED)
    
    mock_repository.get_action_basics.side_effect = [a1, a2]
    
    with pytest.raises(DependencyCycleError):
        await service.add_dependency(workspace_id, a1.id, a2.id)


@pytest.mark.asyncio
async def test_concurrent_lock_serialization(mock_repository):
    """
    Tests that pg_advisory_xact_lock forces concurrent graph mutations 
    in the same workspace to serialize perfectly.
    """
    session = MockSessionWithLock()
    service = ActionPlanningService(session, mock_repository)
    
    workspace_id = uuid.uuid4()
    
    a1 = Action(id=uuid.uuid4(), workspace_id=workspace_id, status=ActionStatus.PLANNED)
    a2 = Action(id=uuid.uuid4(), workspace_id=workspace_id, status=ActionStatus.PLANNED)
    
    # We must patch get_action_basics to return safely multiple times
    mock_repository.get_action_basics.return_value = a1
    
    # Run two mutations concurrently
    # They should serialize: Lock -> check -> flush -> save -> (mock_repo calls commit which releases lock)
    # Wait, our MockSessionWithLock.commit releases the lock, but repo.save() does it?
    # Actually, in the real code, repo.save() calls session.commit().
    # Let's mock repo.save to call session.commit
    async def mock_save():
        await session.commit()
    mock_repository.save = AsyncMock(side_effect=mock_save)
    
    await asyncio.gather(
        service.add_dependency(workspace_id, a1.id, a2.id),
        service.add_dependency(workspace_id, a2.id, a1.id)
    )
    
    # If they serialize, the log will show: lock, check, flush, commit, lock, check, flush, commit
    # If they interleaved, it would be: lock, lock, check, check... (but lock prevents this)
    
    # Verify the lock ID was identical
    lock_events = [e for e in session.execution_log if isinstance(e, tuple)]
    assert lock_events[0][1] == lock_events[1][1]
    
    # Ensure they did not interleave
    assert session.execution_log[:5] == [
        lock_events[0], "cycle_check", "add", "flush", "commit"
    ]
    assert session.execution_log[5:] == [
        lock_events[1], "cycle_check", "add", "flush", "commit"
    ]


@pytest.mark.asyncio
async def test_concurrent_workspace_independence(mock_repository):
    """
    Tests that pg_advisory_xact_lock scopes by workspace, allowing 
    concurrent graph mutations in DIFFERENT workspaces to run in parallel.
    """
    session = MockSessionWithLock()
    service = ActionPlanningService(session, mock_repository)
    
    workspace_id_1 = uuid.uuid4()
    workspace_id_2 = uuid.uuid4()
    
    a1 = Action(id=uuid.uuid4(), workspace_id=workspace_id_1, status=ActionStatus.PLANNED)
    a2 = Action(id=uuid.uuid4(), workspace_id=workspace_id_2, status=ActionStatus.PLANNED)
    
    async def mock_get_basics(action_id):
        if action_id == a1.id:
            return a1
        return a2
        
    mock_repository.get_action_basics = AsyncMock(side_effect=mock_get_basics)
    
    async def mock_save():
        # In a real async scenario, the commit takes some time
        await asyncio.sleep(0.02)
        await session.commit()
    mock_repository.save = AsyncMock(side_effect=mock_save)
    
    await asyncio.gather(
        service.add_dependency(workspace_id_1, a1.id, a1.id), # just re-using a1 for simplicity
        service.add_dependency(workspace_id_2, a2.id, a2.id)
    )
    
    lock_events = [e for e in session.execution_log if isinstance(e, tuple)]
    # Lock IDs must differ
    assert lock_events[0][1] != lock_events[1][1]
    
    # Since locks differ, they should run in parallel, meaning both locks acquire before commits
    assert lock_events[0] in session.execution_log[:2]
    assert lock_events[1] in session.execution_log[:2]


@pytest.mark.asyncio
async def test_idempotent_duplicate(mock_repository):
    session = MockSessionWithLock()
    service = ActionPlanningService(session, mock_repository)
    
    workspace_id = uuid.uuid4()
    a1 = Action(id=uuid.uuid4(), workspace_id=workspace_id, status=ActionStatus.PLANNED)
    mock_repository.get_action_basics.return_value = a1
    
    async def mock_flush():
        session.execution_log.append("flush")
        raise IntegrityError("mock", "mock", "mock")
        
    session.flush = AsyncMock(side_effect=mock_flush)
    
    # This should not raise an exception, it should return silently (idempotent)
    await service.add_dependency(workspace_id, a1.id, a1.id)
    
    assert "rollback" in session.execution_log
