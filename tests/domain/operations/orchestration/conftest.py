"""
conftest.py — Shared fixtures for Phase 3.5 orchestration tests.

All fixtures use mocks — no real database, no real event bus, no real
ExecutionPort I/O. This mirrors the Phase 3.4 test pattern.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.domain.operations.models import ActionStatus, ActionPriority, ActionType
from app.domain.operations.schemas import ActionReadiness
from app.domain.operations.orchestration.engine import ActionOrchestrationEngine
from app.domain.operations.orchestration.port import ExecutionPort, NoopExecutionPort
from app.domain.operations.orchestration.schemas import OrchestrateActionRequest
from app.utils.clock import SystemClock


# ──────────────────────────────────────────────────────────────────────
#  Common UUIDs
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def workspace_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def action_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def dep_action_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def pinned_revision_id() -> str:
    return "rev-pinned-001"


# ──────────────────────────────────────────────────────────────────────
#  Approved Action mock
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def approved_action(workspace_id, action_id, pinned_revision_id):
    """
    An Action mock in APPROVED status with a known revision_id.
    Simulates the state immediately after Phase 3.4 governance approval.
    """
    action = MagicMock()
    action.id = action_id
    action.workspace_id = workspace_id
    action.status = ActionStatus.APPROVED
    action.revision_id = pinned_revision_id
    action.version_number = 2
    action.priority = ActionPriority.NORMAL
    action.action_type = ActionType.CREATE_FOLLOWUP
    action.target = {}
    action.execution_metadata = {}
    action.advance_revision = MagicMock()
    return action


# ──────────────────────────────────────────────────────────────────────
#  Repository mock
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session():
    mock_sess = AsyncMock()
    def mock_add(obj):
        import uuid
        from datetime import datetime, timezone
        if not getattr(obj, "id", None): obj.id = uuid.uuid4()
        if hasattr(obj, "run") and getattr(obj, "run", None): obj.run_id = obj.run.id
        if hasattr(obj, "started_at") and not getattr(obj, "started_at", None): obj.started_at = datetime.now(timezone.utc)
        if hasattr(obj, "created_at") and not getattr(obj, "created_at", None): obj.created_at = datetime.now(timezone.utc)
        if hasattr(obj, "updated_at") and not getattr(obj, "updated_at", None): obj.updated_at = datetime.now(timezone.utc)
    mock_sess.add = MagicMock(side_effect=mock_add)
    mock_sess.commit = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    mock_sess.execute = AsyncMock(return_value=mock_result)
    return mock_sess

@pytest.fixture
def mock_repository(approved_action, mock_session):
    repo = AsyncMock()
    repo.get_action = AsyncMock(return_value=approved_action)
    repo.save = AsyncMock()
    # Expose a mock session for blocker-status queries inside _assert_readiness
    repo.session = mock_session
    return repo


# ──────────────────────────────────────────────────────────────────────
#  Planning service mock (READY — no blockers)
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_planning_service(action_id):
    svc = AsyncMock()
    svc.evaluate_readiness = AsyncMock(return_value=ActionReadiness(
        action_id=action_id,
        state="READY",
        blockers=[],
        satisfied_dependencies=[],
        action_version=2,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    ))
    return svc


# ──────────────────────────────────────────────────────────────────────
#  ExecutionPort mock
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_execution_port():
    port = AsyncMock(spec=ExecutionPort)
    port.submit = AsyncMock(return_value="handle-001")
    return port


# ──────────────────────────────────────────────────────────────────────
#  Event bus mock
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_event_bus():
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


# ──────────────────────────────────────────────────────────────────────
#  ActionOrchestrationEngine factory fixture
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def orch_engine(mock_session, mock_repository, mock_planning_service, mock_execution_port, mock_event_bus):
    return ActionOrchestrationEngine(
        session=mock_session,
        repository=mock_repository,
        planning_service=mock_planning_service,
        execution_port=mock_execution_port,
        event_bus=mock_event_bus,
    )


# ──────────────────────────────────────────────────────────────────────
#  Default orchestrate request
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def orchestrate_req(pinned_revision_id):
    return OrchestrateActionRequest(pinned_revision_id=pinned_revision_id, pinned_action_version=2)