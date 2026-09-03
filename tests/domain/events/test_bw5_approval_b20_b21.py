"""
BW5 Certification Test — B20 (Approval Segregation of Duties) + B21 (Policy Version Pinning)

Tests run against real PostgreSQL.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select

# ── Bootstrap SQLAlchemy mapper order ─────────────────────────────────────────
# Customer must be imported before ApprovalPolicy (or any model that depends on
# conversations.Base relationships) to prevent mapper initialization errors.
from app.domain.customers.models import Customer  # noqa: F401 — must be first
from app.domain.conversations.models import Conversation  # noqa: F401
from app.domain.approval.models import (
    ApprovalPolicy,
    ApprovalRequest,
    ApprovalDecision,
    ApprovalStatus,
)
from app.domain.approval.engine import ApprovalEngine
from app.domain.approval.schemas import MakeDecisionRequest


# ── helpers ──────────────────────────────────────────────────────────────────

def make_policy(workspace_id, require_sod: bool = True, approver_ids=None):
    """Minimal ApprovalPolicy ORM object."""
    approver_ids = approver_ids or ["approver-alice"]
    return ApprovalPolicy(
        workspace_id=workspace_id,
        name="High-Risk Action Policy",
        enabled=True,
        priority=100,
        matching_conditions=[],
        stages=[{
            "stage_index": 0,
            "type": "single",
            "approver_ids": approver_ids,
            "required_count": 1,
        }],
        timeout_hours=48,
        require_segregation_of_duties=require_sod,
    )


def make_request(workspace_id, policy_id, requested_by, policy_snapshot):
    """Minimal ApprovalRequest in UNDER_REVIEW state, with policy snapshot."""
    return ApprovalRequest(
        workspace_id=workspace_id,
        action_id=uuid.uuid4(),
        action_version=1,
        policy_id=policy_id,
        status=ApprovalStatus.UNDER_REVIEW.value,
        current_stage_index=0,
        requested_by=requested_by,
        action_summary="Delete all customer data",
        risk_level="HIGH",
        policy_snapshot=policy_snapshot,
        policy_version_at_request="2026-09-01T00:00:00",
    )


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def pg_session_approval(pg_engine):
    """Create all tables including approval tables and yield an async session."""
    from app.domain.conversations.models import Base
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


# ── B20 tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_b20_self_approval_blocked(pg_session_approval):
    """
    B20 — Segregation of Duties:
    The requester (bob) attempts to approve their own request.
    Policy has require_segregation_of_duties=True.
    Expect: PermissionError raised.
    """
    session = pg_session_approval
    workspace_id = uuid.uuid4()
    requester = "user-bob"

    # Create policy with SoD enabled
    policy = make_policy(workspace_id, require_sod=True, approver_ids=["user-bob", "approver-alice"])
    session.add(policy)
    await session.flush()
    await session.refresh(policy)

    # Build snapshot and approval request
    snapshot = {
        "id": str(policy.id),
        "name": policy.name,
        "stages": policy.stages,
        "timeout_hours": policy.timeout_hours,
        "require_segregation_of_duties": True,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    req = make_request(workspace_id, policy.id, requester, snapshot)
    session.add(req)
    await session.flush()
    await session.refresh(req)

    # bob tries to approve his own request
    decision_req = MakeDecisionRequest(approver_id=requester, decision="APPROVED")

    from unittest.mock import AsyncMock, MagicMock
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()

    from app.domain.approval.engine import ApprovalEngine
    engine = ApprovalEngine(session=session, event_bus=event_bus)

    with pytest.raises(PermissionError, match="Segregation of duties violation"):
        await engine.process_decision(req.id, decision_req, authenticated_actor_id=requester)


@pytest.mark.asyncio
async def test_b20_authorized_approver_succeeds(pg_session_approval):
    """
    B20 — Authorized approver (alice) approves the request.
    Requester was bob. Policy allows alice. SoD=True.
    Expect: request transitions to APPROVED.
    """
    session = pg_session_approval
    workspace_id = uuid.uuid4()
    requester = "user-bob"
    approver = "approver-alice"

    policy = make_policy(workspace_id, require_sod=True, approver_ids=[approver])
    session.add(policy)
    await session.flush()
    await session.refresh(policy)

    snapshot = {
        "id": str(policy.id),
        "name": policy.name,
        "stages": policy.stages,
        "timeout_hours": policy.timeout_hours,
        "require_segregation_of_duties": True,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    req = make_request(workspace_id, policy.id, requester, snapshot)
    session.add(req)
    await session.flush()
    await session.refresh(req)

    decision_req = MakeDecisionRequest(approver_id=approver, decision="APPROVED")

    from unittest.mock import AsyncMock
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()

    engine = ApprovalEngine(session=session, event_bus=event_bus)
    result = await engine.process_decision(req.id, decision_req, authenticated_actor_id=approver)

    assert result.status == ApprovalStatus.APPROVED.value, f"Expected APPROVED, got {result.status}"


@pytest.mark.asyncio
async def test_b20_unauthorized_actor_rejected(pg_session_approval):
    """
    B20 — An actor not in the allowed approvers list cannot approve.
    Expect: PermissionError.
    """
    session = pg_session_approval
    workspace_id = uuid.uuid4()
    requester = "user-bob"
    approver = "approver-alice"
    intruder = "user-eve"

    policy = make_policy(workspace_id, require_sod=True, approver_ids=[approver])
    session.add(policy)
    await session.flush()
    await session.refresh(policy)

    snapshot = {
        "id": str(policy.id),
        "name": policy.name,
        "stages": policy.stages,
        "timeout_hours": policy.timeout_hours,
        "require_segregation_of_duties": True,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    req = make_request(workspace_id, policy.id, requester, snapshot)
    session.add(req)
    await session.flush()
    await session.refresh(req)

    decision_req = MakeDecisionRequest(approver_id=intruder, decision="APPROVED")

    from unittest.mock import AsyncMock
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()

    engine = ApprovalEngine(session=session, event_bus=event_bus)

    with pytest.raises(PermissionError, match="not authorized"):
        await engine.process_decision(req.id, decision_req, authenticated_actor_id=intruder)


@pytest.mark.asyncio
async def test_b20_cross_workspace_isolation(pg_session_approval):
    """
    B20 Workspace isolation: approver from workspace B cannot approve workspace A request.
    The approver_ids list only contains workspace-A actor.
    """
    session = pg_session_approval
    workspace_a = uuid.uuid4()
    workspace_b = uuid.uuid4()

    approver_a = "approver-ws-a"
    approver_b = "approver-ws-b"
    requester = "user-bob-ws-a"

    policy = make_policy(workspace_a, require_sod=True, approver_ids=[approver_a])
    session.add(policy)
    await session.flush()
    await session.refresh(policy)

    snapshot = {
        "id": str(policy.id),
        "name": policy.name,
        "stages": policy.stages,
        "timeout_hours": policy.timeout_hours,
        "require_segregation_of_duties": True,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    req = make_request(workspace_a, policy.id, requester, snapshot)
    session.add(req)
    await session.flush()
    await session.refresh(req)

    decision_req = MakeDecisionRequest(approver_id=approver_b, decision="APPROVED")

    from unittest.mock import AsyncMock
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()

    engine = ApprovalEngine(session=session, event_bus=event_bus)

    with pytest.raises(PermissionError, match="not authorized"):
        await engine.process_decision(req.id, decision_req, authenticated_actor_id=approver_b)


# ── B21 tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_b21_pinned_policy_used_even_after_policy_change(pg_session_approval):
    """
    B21 — Policy Version Pinning:
    1. Create request with policy v1 (approver=alice, SoD=True).
    2. Mutate the live policy to v2 (approver=charlie, SoD=False).
    3. Approve using the original pinned snapshot context (alice).
    Result: alice's approval succeeds because the PINNED snapshot is used.
    charlie would have been the only person allowed by the live v2 policy,
    but the snapshot correctly uses the v1 stages.
    """
    session = pg_session_approval
    workspace_id = uuid.uuid4()
    requester = "user-bob"
    approver_v1 = "approver-alice"
    approver_v2 = "approver-charlie"

    # Create policy v1
    policy = make_policy(workspace_id, require_sod=True, approver_ids=[approver_v1])
    session.add(policy)
    await session.flush()
    await session.refresh(policy)

    # Snapshot at v1
    snapshot_v1 = {
        "id": str(policy.id),
        "name": policy.name,
        "stages": policy.stages,  # approver=alice
        "timeout_hours": policy.timeout_hours,
        "require_segregation_of_duties": True,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }

    req = make_request(workspace_id, policy.id, requester, snapshot_v1)
    session.add(req)
    await session.flush()
    await session.refresh(req)

    # Mutate the live policy to v2 (different approver, SoD disabled)
    policy.stages = [{"stage_index": 0, "type": "single", "approver_ids": [approver_v2], "required_count": 1}]
    policy.require_segregation_of_duties = False
    await session.flush()

    # Approve using alice — who was authorized in the PINNED v1 snapshot
    decision_req = MakeDecisionRequest(approver_id=approver_v1, decision="APPROVED")

    from unittest.mock import AsyncMock
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()

    engine = ApprovalEngine(session=session, event_bus=event_bus)
    result = await engine.process_decision(req.id, decision_req, authenticated_actor_id=approver_v1)

    assert result.status == ApprovalStatus.APPROVED.value, (
        f"Expected APPROVED using pinned v1 policy, got {result.status}"
    )

    # Confirm that the policy_snapshot on the request still reflects v1
    await session.refresh(req)
    assert req.policy_snapshot is not None
    pinned_stages = req.policy_snapshot.get("stages", [])
    assert pinned_stages[0]["approver_ids"] == [approver_v1], (
        "Pinned snapshot should still reference alice, not charlie"
    )


@pytest.mark.asyncio
async def test_b21_sod_enforced_from_pinned_snapshot(pg_session_approval):
    """
    B21 — SoD comes from the pinned snapshot, not the mutated live policy.
    1. Create policy with SoD=True, approver=[bob].
    2. Mutate live policy to SoD=False.
    3. Bob (requester) tries to approve.
    Result: PermissionError — because the PINNED snapshot still has SoD=True.
    """
    session = pg_session_approval
    workspace_id = uuid.uuid4()
    requester = "user-bob"

    policy = make_policy(workspace_id, require_sod=True, approver_ids=[requester])
    session.add(policy)
    await session.flush()
    await session.refresh(policy)

    snapshot_v1 = {
        "id": str(policy.id),
        "name": policy.name,
        "stages": policy.stages,
        "timeout_hours": policy.timeout_hours,
        "require_segregation_of_duties": True,  # pinned to True
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }

    req = make_request(workspace_id, policy.id, requester, snapshot_v1)
    session.add(req)
    await session.flush()
    await session.refresh(req)

    # Mutate live policy to disable SoD (trying to bypass)
    policy.require_segregation_of_duties = False
    await session.flush()

    decision_req = MakeDecisionRequest(approver_id=requester, decision="APPROVED")

    from unittest.mock import AsyncMock
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()

    engine = ApprovalEngine(session=session, event_bus=event_bus)

    with pytest.raises(PermissionError, match="Segregation of duties violation"):
        await engine.process_decision(req.id, decision_req, authenticated_actor_id=requester)
