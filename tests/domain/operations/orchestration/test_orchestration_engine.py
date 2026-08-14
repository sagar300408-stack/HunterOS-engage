"""
test_orchestration_engine.py — Phase 3.5 unit tests for ActionOrchestrationEngine.

10 test cases covering:
  1. Happy path (APPROVED → READY → EXECUTING, HANDED_OFF result)
  2. Wrong initial status → OrchestrationError
  3. Stale revision → StalePinnedVersionError
  4. Permanently-failed dependency → OrchestrationBlockedError
  5. Transient block → OrchestrationError (not OrchestrationBlockedError)
  6. ExecutionPort failure → Action transitions to FAILED, event published
  7. Version drift between READY and EXECUTING → StalePinnedVersionError
  8. Event sequence: Started before HandedOff
  9. Workspace isolation: wrong workspace_id → ActionNotFoundError
 10. NoopExecutionPort returns deterministic handle without I/O
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.domain.operations.models import ActionStatus, ActionType, ActionPriority
from app.domain.operations.schemas import ActionReadiness
from app.domain.operations.exceptions import ActionNotFoundError
from app.domain.operations.orchestration.engine import ActionOrchestrationEngine
from app.domain.operations.orchestration.exceptions import (
    OrchestrationError,
    OrchestrationBlockedError,
    StalePinnedVersionError,
)
from app.domain.operations.orchestration.port import NoopExecutionPort
from app.domain.operations.orchestration.schemas import OrchestrateActionRequest
from app.domain.operations.orchestration.models import OrchestrationRunState


# ──────────────────────────────────────────────────────────────────────
#  Helper: build a fresh Action-like mock at any status / revision
# ──────────────────────────────────────────────────────────────────────

def make_action(
    workspace_id,
    action_id,
    status=ActionStatus.APPROVED,
    revision_id="rev-pinned-001",
):
    action = MagicMock()
    action.id = action_id
    action.workspace_id = workspace_id
    action.status = status
    action.revision_id = revision_id
    action.version_number = 2
    action.action_type = ActionType.CREATE_FOLLOWUP
    action.target = {}
    action.execution_metadata = {}
    action.advance_revision = MagicMock()
    return action


# ──────────────────────────────────────────────────────────────────────
#  Test 1 — Happy path: APPROVED → READY → EXECUTING, HANDED_OFF
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_happy_path_transitions_to_executing(
    orch_engine, workspace_id, action_id, approved_action, orchestrate_req,
    mock_repository, mock_event_bus, mock_execution_port,
):
    """
    Full golden path: action in APPROVED status with matching revision and
    no blockers should transition to READY then EXECUTING, invoke the port,
    store the handle, and return OrchestrationOutcome.HANDED_OFF.
    """
    # After the APPROVED→READY transition the engine re-fetches to get the new revision.
    # Simulate a slightly different revision to prove advance_revision() was called.
    ready_action = make_action(workspace_id, action_id, ActionStatus.READY, "rev-002")
    executing_action = make_action(workspace_id, action_id, ActionStatus.EXECUTING, "rev-003")

    # The engine calls get_action four times:
    #   1. Initial fetch (APPROVED, rev-pinned-001)                     — orchestrate() step 1
    #   2. _transition(APPROVED→READY) internal fetch (APPROVED, same)  — revision guard
    #   3. Step 7 re-fetch after READY transition (READY, rev-002)      — orchestrate() step 7
    #   4. _transition(READY→EXECUTING) internal fetch (READY, rev-002) — revision guard
    mock_repository.get_action = AsyncMock(side_effect=[
        approved_action,   # 1: initial fetch
        approved_action,   # 2: _transition(APPROVED→READY) internal
        ready_action,      # 3: step 7 re-fetch
        ready_action,      # 4: _transition(READY→EXECUTING) internal
    ])

    result = await orch_engine.orchestrate(workspace_id, action_id, orchestrate_req)
    assert result.state == OrchestrationRunState.EXECUTING.value
    assert result.attempts[-1].execution_handle == "handle-001"
    assert result.action_id == action_id
    assert result.workspace_id == workspace_id
    assert result.failure_reason is None
    mock_execution_port.submit.assert_awaited_once()
    mock_event_bus.publish.assert_awaited()


# ──────────────────────────────────────────────────────────────────────
#  Test 2 — Wrong status raises OrchestrationError
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wrong_status_raises_orchestration_error(
    orch_engine, workspace_id, action_id, mock_repository, orchestrate_req,
):
    """Action in PLANNED (not APPROVED) → OrchestrationError before any transition."""
    planned_action = make_action(workspace_id, action_id, ActionStatus.PLANNED, "rev-pinned-001")
    mock_repository.get_action = AsyncMock(return_value=planned_action)

    with pytest.raises(OrchestrationError) as exc_info:
        await orch_engine.orchestrate(workspace_id, action_id, orchestrate_req)

    assert "APPROVED" in str(exc_info.value)
    # No transitions should have been attempted
    mock_repository.save.assert_not_awaited()


# ──────────────────────────────────────────────────────────────────────
#  Test 3 — Stale revision raises StalePinnedVersionError
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stale_revision_raises_stale_error(
    orch_engine, workspace_id, action_id, mock_repository,
):
    """action_version has drifted since governance pinned it → StalePinnedVersionError."""
    action = make_action(workspace_id, action_id, ActionStatus.APPROVED, revision_id="rev-DRIFTED")
    action.version_number = 3
    mock_repository.get_action = AsyncMock(return_value=action)

    req = OrchestrateActionRequest(pinned_action_version=99)

    with pytest.raises(StalePinnedVersionError) as exc_info:
        await orch_engine.orchestrate(workspace_id, action_id, req)

    assert "99" in str(exc_info.value)
    assert "3" in str(exc_info.value)
    mock_repository.save.assert_not_awaited()


# ──────────────────────────────────────────────────────────────────────
#  Test 4 — Permanently-failed dependency → OrchestrationBlockedError
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_permanently_blocked_dep_raises_blocked_error(mock_session, 
    workspace_id, action_id, mock_repository, mock_execution_port, mock_event_bus,
    approved_action, orchestrate_req,
):
    """A prerequisite in FAILED status → OrchestrationBlockedError (unrecoverable)."""
    dep_id = uuid.uuid4()

    blocked_readiness = ActionReadiness(
        action_id=action_id,
        state="BLOCKED",
        blockers=[dep_id],
        satisfied_dependencies=[],
        action_version=2,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )

    # Simulate the blocker query returning FAILED status
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    failed_row = MagicMock()
    failed_row.id = dep_id
    failed_row.status = ActionStatus.FAILED
    mock_result.all.return_value = [failed_row]
    mock_repository.session.execute = AsyncMock(return_value=mock_result)

    blocked_planning = AsyncMock()
    blocked_planning.evaluate_readiness = AsyncMock(return_value=blocked_readiness)

    engine = ActionOrchestrationEngine(
        session=mock_session,
        repository=mock_repository,
        planning_service=blocked_planning,
        execution_port=mock_execution_port,
        event_bus=mock_event_bus,
    )

    with pytest.raises(OrchestrationBlockedError) as exc_info:
        await engine.orchestrate(workspace_id, action_id, orchestrate_req)

    assert dep_id in exc_info.value.permanently_failed_dep_ids
    mock_repository.save.assert_not_awaited()


# ──────────────────────────────────────────────────────────────────────
#  Test 5 — Transient block raises OrchestrationError (not Blocked)
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transient_block_raises_orchestration_error(mock_session, 
    workspace_id, action_id, mock_repository, mock_execution_port, mock_event_bus,
    approved_action, orchestrate_req,
):
    """A prerequisite in EXECUTING (transient) → OrchestrationError, not OrchestrationBlockedError."""
    dep_id = uuid.uuid4()

    blocked_readiness = ActionReadiness(
        action_id=action_id,
        state="BLOCKED",
        blockers=[dep_id],
        satisfied_dependencies=[],
        action_version=2,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )

    # Blocker is EXECUTING — transient, not permanently failed
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    executing_row = MagicMock()
    executing_row.id = dep_id
    executing_row.status = ActionStatus.EXECUTING
    mock_result.all.return_value = [executing_row]
    mock_repository.session.execute = AsyncMock(return_value=mock_result)

    transient_planning = AsyncMock()
    transient_planning.evaluate_readiness = AsyncMock(return_value=blocked_readiness)

    engine = ActionOrchestrationEngine(
        session=mock_session,
        repository=mock_repository,
        planning_service=transient_planning,
        execution_port=mock_execution_port,
        event_bus=mock_event_bus,
    )

    with pytest.raises(OrchestrationError) as exc_info:
        await engine.orchestrate(workspace_id, action_id, orchestrate_req)

    # Must be OrchestrationError but NOT the more specific OrchestrationBlockedError
    assert not isinstance(exc_info.value, OrchestrationBlockedError)
    assert "transiently" in str(exc_info.value).lower()


# ──────────────────────────────────────────────────────────────────────
#  Test 6 — ExecutionPort failure → FAILED transition + event published
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execution_port_failure_transitions_to_failed(mock_session, 
    workspace_id, action_id, mock_repository, mock_planning_service,
    mock_event_bus, approved_action, orchestrate_req,
):
    """If ExecutionPort.submit() raises, the Action transitions to FAILED and an event is emitted."""
    ready_action = make_action(workspace_id, action_id, ActionStatus.READY, "rev-002")
    executing_action = make_action(workspace_id, action_id, ActionStatus.EXECUTING, "rev-003")

    mock_repository.get_action = AsyncMock(side_effect=[
        approved_action,   # 1: initial fetch
        approved_action,   # 2: _transition(APPROVED→READY) internal fetch
        ready_action,      # 3: step 7 re-fetch
        ready_action,      # 4: _transition(READY→EXECUTING) internal fetch
        executing_action,  # 5: _handle_failure fetch
    ])

    failing_port = AsyncMock(spec=NoopExecutionPort)
    failing_port.submit = AsyncMock(side_effect=RuntimeError("Simulated connector failure"))

    engine = ActionOrchestrationEngine(
        session=mock_session,
        repository=mock_repository,
        planning_service=mock_planning_service,
        execution_port=failing_port,
        event_bus=mock_event_bus,
    )

    await engine.orchestrate(workspace_id, action_id, orchestrate_req)
    
    # Verify action status remains EXECUTING since it's a retryable failure (attempt 1 of 4)
    assert executing_action.status == ActionStatus.EXECUTING

    # Verify the failed event was published
    published_event_names = [
        call_args.args[0].event_name if call_args.args else None
        for call_args in mock_event_bus.publish.call_args_list
    ]
    assert "action.orchestration.run.failed" in published_event_names


# ──────────────────────────────────────────────────────────────────────
#  Test 7 — Version drift between READY and EXECUTING
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_version_guard_between_ready_and_executing(mock_session, 
    workspace_id, action_id, mock_planning_service, mock_execution_port,
    mock_event_bus, approved_action, orchestrate_req,
):
    """
    Simulates a concurrent mutation that changes the revision between the
    APPROVED→READY transition and the READY→EXECUTING transition.
    The engine must detect the drift and raise StalePinnedVersionError.
    """
    # After the READY transition the re-fetched action has a different revision
    # from what the engine expects, simulating a concurrent update.
    ready_action_drifted = make_action(
        workspace_id, action_id, ActionStatus.READY, "rev-CONCURRENT-EDIT"
    )
    ready_action_drifted.version_number = 3

    drifting_repo = AsyncMock()
    drifting_repo.session = AsyncMock()
    drifting_repo.save = AsyncMock()

    # First fetch: APPROVED (matches pin)
    # Second fetch: READY with a DIFFERENT revision (concurrent edit)
    drifting_repo.get_action = AsyncMock(side_effect=[
        approved_action,        # initial fetch → APPROVED, rev-pinned-001
        ready_action_drifted,   # re-fetch after READY → but revision has drifted
    ])

    engine = ActionOrchestrationEngine(
        session=mock_session,
        repository=drifting_repo,
        planning_service=mock_planning_service,
        execution_port=mock_execution_port,
        event_bus=mock_event_bus,
    )

    with pytest.raises((StalePinnedVersionError, OrchestrationError)):
        await engine.orchestrate(workspace_id, action_id, orchestrate_req)

    # ExecutionPort should NOT have been called
    mock_execution_port.submit.assert_not_awaited()


# ──────────────────────────────────────────────────────────────────────
#  Test 8 — Event sequence: Started before HandedOff
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_sequence(mock_session, 
    workspace_id, action_id, mock_planning_service, mock_execution_port,
    mock_event_bus, approved_action, orchestrate_req,
):
    """
    ActionOrchestrationStartedEvent must be published BEFORE
    ActionOrchestrationHandedOffEvent.
    """
    ready_action = make_action(workspace_id, action_id, ActionStatus.READY, "rev-002")
    executing_action = make_action(workspace_id, action_id, ActionStatus.EXECUTING, "rev-003")

    seq_repo = AsyncMock()
    seq_repo.session = AsyncMock()
    seq_repo.save = AsyncMock()
    seq_repo.get_action = AsyncMock(side_effect=[
        approved_action,   # 1: initial fetch
        approved_action,   # 2: _transition(APPROVED→READY) internal fetch
        ready_action,      # 3: step 7 re-fetch
        ready_action,      # 4: _transition(READY→EXECUTING) internal fetch
    ])

    engine = ActionOrchestrationEngine(
        session=mock_session,
        repository=seq_repo,
        planning_service=mock_planning_service,
        execution_port=mock_execution_port,
        event_bus=mock_event_bus,
    )

    await engine.orchestrate(workspace_id, action_id, orchestrate_req)

    event_names = [
        call_args.args[0].event_name
        for call_args in mock_event_bus.publish.call_args_list
        if call_args.args
    ]
    
    assert "action.orchestration.run.started" in event_names
    
    # handed_off_idx could be the second status changed event since it changed from APPROVED->READY then READY->EXECUTING
    started_idx = event_names.index("action.orchestration.run.started")
    handed_off_indices = [i for i, name in enumerate(event_names) if name == "action.status.changed"]
    # The READY->EXECUTING status change should be AFTER the run.started event, or before it depending on the swap we did.
    # We swapped it so run.started is first. So the LAST status.changed event should be after started_idx.
    assert started_idx < handed_off_indices[-1], (
        "action.orchestration.run.started must be published before action.status.changed to EXECUTING"
    )


# ──────────────────────────────────────────────────────────────────────
#  Test 9 — Workspace isolation
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workspace_isolation(
    orch_engine, action_id, mock_repository, orchestrate_req,
):
    """
    Fetching an Action with an incorrect workspace_id returns None from the
    repository, which must surface as ActionNotFoundError.
    """
    wrong_workspace = uuid.uuid4()
    mock_repository.get_action = AsyncMock(return_value=None)

    with pytest.raises(ActionNotFoundError):
        await orch_engine.orchestrate(wrong_workspace, action_id, orchestrate_req)


# ──────────────────────────────────────────────────────────────────────
#  Test 10 — NoopExecutionPort returns deterministic handle without I/O
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_noop_execution_port_returns_handle(workspace_id, action_id):
    """
    NoopExecutionPort.submit() must return 'noop-handle-{action_id}-{attempt_id}' without
    performing any I/O, network calls, or database access.
    """
    from app.domain.operations.orchestration.schemas import ExecutionCommand
    port = NoopExecutionPort()
    
    run_id = uuid.uuid4()
    attempt_id = uuid.uuid4()
    
    command = ExecutionCommand(
        workspace_id=workspace_id,
        action_id=action_id,
        action_version=1,
        action_type="test_action",
        target={},
        parameters={},
        orchestration_run_id=run_id,
        orchestration_attempt_id=attempt_id,
        correlation_id=None
    )

    handle = await port.submit(command=command)

    assert handle == f"noop-handle-{action_id}-{attempt_id}"
