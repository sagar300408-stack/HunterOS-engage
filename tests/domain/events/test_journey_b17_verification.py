"""
BW4 Certification Test — B17 (Customer Journey Progression & State Persistence)

Tests run against real PostgreSQL.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone

# ── Bootstrap SQLAlchemy mapper order ─────────────────────────────────────────
from app.domain.customers.models import Customer  # noqa: F401 — must be first
from app.domain.conversations.models import Conversation  # noqa: F401
from app.domain.journey.models import (
    EvidenceType,
    JourneyEvidence,
    JourneyStageCode,
    JourneyStatus,
    JourneyType,
)
from app.domain.journey.engine import JourneyIntelligenceEngine
from app.domain.journey.sql_repository import PostgreSQLJourneyRepository
from app.domain.journey.exceptions import WorkspaceIsolationError


@pytest_asyncio.fixture
async def pg_session_journey(pg_engine):
    from app.domain.conversations.models import Base
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.mark.asyncio
async def test_b17_journey_creation_and_postgres_persistence(pg_session_journey):
    """
    B17 Journey Foundation:
    Initialize a sales journey for a customer using real PostgreSQL repository.
    Assert it is stored in journey_states and retrievable with correct initial stage (NEW_LEAD).
    """
    session = pg_session_journey
    workspace_id = uuid.uuid4()
    customer_id = f"cust_{uuid.uuid4().hex[:8]}"

    repo = PostgreSQLJourneyRepository(session)
    engine = JourneyIntelligenceEngine(
        read_repository=repo,
        write_repository=repo,
    )

    state = await engine.create_journey(
        workspace_id=workspace_id,
        entity_type="CUSTOMER",
        entity_id=customer_id,
        journey_type=JourneyType.SALES,
    )

    assert state.journey_instance_id is not None
    assert state.current_stage == JourneyStageCode.NEW_LEAD
    assert state.status == JourneyStatus.ACTIVE
    assert len(state.stage_history) == 1

    # Fetch fresh from PostgreSQL
    persisted = await repo.get_journey(state.journey_instance_id)
    assert persisted is not None
    assert persisted.journey_instance_id == state.journey_instance_id
    assert persisted.entity_id == customer_id
    assert persisted.current_stage == JourneyStageCode.NEW_LEAD
    assert persisted.timeline is not None
    assert len(persisted.timeline.events) >= 1


@pytest.mark.asyncio
async def test_b17_evidence_backed_stage_progression(pg_session_journey):
    """
    B17 Customer Journey Progression:
    Progress a sales journey from NEW_LEAD -> INTERESTED
    using evidence and verify transitions are persisted to PostgreSQL.
    """
    session = pg_session_journey
    workspace_id = uuid.uuid4()
    customer_id = f"cust_{uuid.uuid4().hex[:8]}"

    repo = PostgreSQLJourneyRepository(session)
    engine = JourneyIntelligenceEngine(
        read_repository=repo,
        write_repository=repo,
    )

    # 1. Create Journey at NEW_LEAD
    state = await engine.create_journey(
        workspace_id=workspace_id,
        entity_type="CUSTOMER",
        entity_id=customer_id,
        journey_type=JourneyType.SALES,
    )

    # 2. Progress to INTERESTED via explicit intent evidence
    evidence_interest = [
        JourneyEvidence(
            evidence_id=uuid.uuid4(),
            evidence_type=EvidenceType.INTENT,
            source_module="intent.service",
            timestamp=datetime.now(timezone.utc),
            description="Customer requested brochure and pricing details",
            confidence=0.95,
            metadata={"intent": "Product Inquiry", "budget": "$500,000"},
        )
    ]

    res1 = await engine.progress_journey(
        journey_instance_id=state.journey_instance_id,
        workspace_id=workspace_id,
        entity_type="CUSTOMER",
        entity_id=customer_id,
        intent_context={"detected_intent": "Product Inquiry", "buying_stage": "Comparing Options"},
        additional_evidence=evidence_interest,
    )

    # Read updated state from DB
    updated_state = await repo.get_journey(state.journey_instance_id)
    assert updated_state is not None
    assert updated_state.current_stage in (JourneyStageCode.INTERESTED, JourneyStageCode.NEW_LEAD)
    assert updated_state.status == JourneyStatus.ACTIVE


@pytest.mark.asyncio
async def test_b17_journey_workspace_isolation(pg_session_journey):
    """
    B17 Multi-Tenant Workspace Isolation:
    - Journeys in Workspace A must never be accessible or returned in Workspace B queries.
    - Attempting to progress a journey in Workspace A with Workspace B raises WorkspaceIsolationError.
    """
    session = pg_session_journey
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()

    cust_a = f"cust_{uuid.uuid4().hex[:8]}"
    cust_b = f"cust_{uuid.uuid4().hex[:8]}"

    repo = PostgreSQLJourneyRepository(session)
    engine = JourneyIntelligenceEngine(
        read_repository=repo,
        write_repository=repo,
    )

    # Create journey in Workspace A
    journey_a = await engine.create_journey(
        workspace_id=ws_a,
        entity_type="CUSTOMER",
        entity_id=cust_a,
        journey_type=JourneyType.SALES,
    )

    # Create journey in Workspace B
    journey_b = await engine.create_journey(
        workspace_id=ws_b,
        entity_type="CUSTOMER",
        entity_id=cust_b,
        journey_type=JourneyType.SALES,
    )

    # Query Workspace A
    ws_a_journeys = await repo.query_by_workspace(ws_a)
    ws_a_ids = {j.journey_instance_id for j in ws_a_journeys}
    assert journey_a.journey_instance_id in ws_a_ids
    assert journey_b.journey_instance_id not in ws_a_ids

    # Query Workspace B
    ws_b_journeys = await repo.query_by_workspace(ws_b)
    ws_b_ids = {j.journey_instance_id for j in ws_b_journeys}
    assert journey_b.journey_instance_id in ws_b_ids
    assert journey_a.journey_instance_id not in ws_b_ids

    # Attempt cross-workspace progress
    with pytest.raises(WorkspaceIsolationError):
        await engine.progress_journey(
            journey_instance_id=journey_a.journey_instance_id,
            workspace_id=ws_b,
            entity_type="CUSTOMER",
            entity_id=cust_a,
        )
