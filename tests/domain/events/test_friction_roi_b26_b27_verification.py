"""
HunterOS Engage — BW6 Certification Tests
B26: Business Friction Scoring
B27: ROI Calculation

Verification rules:
  - Real PostgreSQL for B26 (FrictionEvent + FrictionScoreSnapshot)
  - ROI formulas verified in isolation (pure math — no DB needed for formula test)
  - B27 DB persistence verified via real ImpactRepository
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# ── Model imports in dependency order ─────────────────────────────────────────
from app.domain.conversations.models import Base, Conversation, Message  # noqa: F401
from app.domain.customers.models import Customer                          # noqa: F401
from app.domain.intent.models import IntentHistory                        # noqa: F401
from app.domain.security.models import User, AuditLog                    # noqa: F401
from app.domain.memory.models import CustomerMemory, CustomerMemoryEvent  # noqa: F401
from app.domain.followup.models import FollowUpQueue, FollowUpExecution   # noqa: F401
from app.domain.leads.models import LeadQualificationSnapshot             # noqa: F401
from app.domain.escalation.models import HumanEscalation                  # noqa: F401
from app.domain.approval.models import (                                  # noqa: F401
    ApprovalPolicy, ApprovalRequest, ApprovalDecision,
)
from app.domain.journey.sql_models import JourneyStateModel               # noqa: F401
from app.domain.recommendation.models import RecommendationSnapshot       # noqa: F401
from app.domain.friction.models import (                                  # noqa: F401
    FrictionEvent, FrictionScoreSnapshot, SLAPolicy, WorkflowStageLatency,
    FrictionType, FrictionResolution, FrictionSeverity,
)
from app.domain.impact.models import (                                    # noqa: F401
    FinancialConfig, BusinessTargets, BaselineMetrics,
    ImpactEvent, EvidenceTrace, ValueAttribution, ExecutiveImpactReport,
    ImpactCategory,
)
from app.domain.context.models import (                                   # noqa: F401
    OrganizationNode, ProductService, WorkflowDefinition, BusinessPolicy,
    CustomerContext, TeamMemberContext, KnowledgeDocument,
    BusinessOntology, KnowledgeGraphEdge, ContextConflict,
)
from app.domain.scheduling.models import (                                # noqa: F401
    ScheduledEvent, SchedulingCandidate, EventAuditLog,
    CustomerAvailabilityPreferences,
)

from app.domain.friction.repository import FrictionRepository
from app.domain.friction.scoring import FrictionScoreEngine, WEIGHT_CONFIG
from app.domain.impact.engines.roi import ROICalculator
from app.domain.impact.repository import ImpactRepository
from app.domain.security.models import DEFAULT_WORKSPACE_ID

pytestmark = pytest.mark.asyncio


# ── Ensure tables exist ───────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def ensure_tables(pg_engine):
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ═════════════════════════════════════════════════════════════════════════════
# B26 — Business Friction Scoring
# ═════════════════════════════════════════════════════════════════════════════

class TestB26FrictionScoring:
    """
    B26 CERTIFICATION: FrictionScoreEngine must query real FrictionEvents,
    apply documented weighted formula (sum of capped contributions, 0–100),
    and persist a FrictionScoreSnapshot.
    """

    async def _insert_friction_events(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        friction_type: str,
        count: int,
    ) -> None:
        """Insert `count` OPEN FrictionEvent rows of the given type."""
        for _ in range(count):
            ev = FrictionEvent(
                workspace_id=workspace_id,
                friction_type=friction_type,
                severity=FrictionSeverity.HIGH.value,
                score_contribution=0.0,
                description=f"B26 test event: {friction_type}",
                resolution_status=FrictionResolution.OPEN.value,
            )
            session.add(ev)
        await session.flush()

    async def test_b26_zero_events_zero_score(self, pg_session: AsyncSession):
        """
        A workspace with no friction events must have a computed BFS of 0.0.
        """
        workspace_id = uuid.uuid4()
        repo = FrictionRepository(pg_session)
        engine = FrictionScoreEngine(repo)

        snapshot = await engine.compute_score(workspace_id)

        assert snapshot.score == 0.0, \
            f"B26: Expected BFS=0.0 for clean workspace, got {snapshot.score}"
        assert snapshot.trend == "STABLE"
        assert snapshot.workspace_id == workspace_id

    async def test_b26_single_type_contribution_capped(self, pg_session: AsyncSession):
        """
        LEAD_RESPONSE_DELAY: max_weight=20, per_event=4.0
        With 10 events: raw contribution = 10 × 4.0 = 40 → capped at 20.
        Final BFS must be 20.0 exactly.
        """
        workspace_id = uuid.uuid4()
        await self._insert_friction_events(
            pg_session, workspace_id,
            friction_type=FrictionType.LEAD_RESPONSE_DELAY.value,
            count=10,
        )
        await pg_session.commit()

        repo = FrictionRepository(pg_session)
        engine = FrictionScoreEngine(repo)
        snapshot = await engine.compute_score(workspace_id)

        assert snapshot.score == 20.0, \
            (f"B26: LEAD_RESPONSE_DELAY with 10 events should cap at 20, "
             f"got {snapshot.score}")
        assert FrictionType.LEAD_RESPONSE_DELAY.value in snapshot.contributors

    async def test_b26_multi_type_weighted_sum(self, pg_session: AsyncSession):
        """
        Insert exactly 1 event of each type.
        Expected contributions:
          LEAD_RESPONSE_DELAY: 1 × 4.0 = 4.0
          MISSED_FOLLOWUP: 1 × 3.0 = 3.0
          SLA_VIOLATION: 1 × 5.0 = 5.0
          APPROVAL_DELAY: 1 × 6.0 = 6.0
          WORKFLOW_STALL: 1 × 5.0 = 5.0
          CUSTOMER_INACTIVITY: 1 × 2.0 = 2.0
          OPPORTUNITY_LEAKAGE: 1 × 3.0 = 3.0
        Total = 28.0
        """
        workspace_id = uuid.uuid4()
        for ftype in [
            FrictionType.LEAD_RESPONSE_DELAY,
            FrictionType.MISSED_FOLLOWUP,
            FrictionType.SLA_VIOLATION,
            FrictionType.APPROVAL_DELAY,
            FrictionType.WORKFLOW_STALL,
            FrictionType.CUSTOMER_INACTIVITY,
            FrictionType.OPPORTUNITY_LEAKAGE,
        ]:
            await self._insert_friction_events(pg_session, workspace_id, ftype.value, 1)
        await pg_session.commit()

        repo = FrictionRepository(pg_session)
        engine = FrictionScoreEngine(repo)
        snapshot = await engine.compute_score(workspace_id)

        assert snapshot.score == pytest.approx(28.0, abs=0.01), \
            f"B26: Expected BFS=28.0 for 1 event per type, got {snapshot.score}"

    async def test_b26_snapshot_persisted(self, pg_session: AsyncSession):
        """
        FrictionScoreEngine.compute_score() must return a FrictionScoreSnapshot
        object — the caller is responsible for persisting it.
        Verify that saving the snapshot via FrictionRepository succeeds.
        """
        workspace_id = uuid.uuid4()
        repo = FrictionRepository(pg_session)
        engine = FrictionScoreEngine(repo)

        snapshot = await engine.compute_score(workspace_id)
        saved = await repo.save_score_snapshot(snapshot)
        await pg_session.commit()

        assert saved.id is not None, \
            "B26: Snapshot must have a valid UUID after persist"
        assert saved.score == snapshot.score

    async def test_b26_score_bounded_0_to_100(self, pg_session: AsyncSession):
        """
        Even with extreme numbers of events, BFS MUST NOT exceed 100.
        """
        workspace_id = uuid.uuid4()
        # Insert 100 events of every type (well above any cap)
        for ftype in FrictionType:
            await self._insert_friction_events(pg_session, workspace_id, ftype.value, 100)
        await pg_session.commit()

        repo = FrictionRepository(pg_session)
        engine = FrictionScoreEngine(repo)
        snapshot = await engine.compute_score(workspace_id)

        assert 0.0 <= snapshot.score <= 100.0, \
            f"B26: BFS must be in [0, 100], got {snapshot.score}"

    async def test_b26_resolved_events_not_counted(self, pg_session: AsyncSession):
        """
        RESOLVED friction events MUST NOT contribute to the BFS.
        """
        workspace_id = uuid.uuid4()
        # Insert 5 resolved events
        for _ in range(5):
            ev = FrictionEvent(
                workspace_id=workspace_id,
                friction_type=FrictionType.LEAD_RESPONSE_DELAY.value,
                severity=FrictionSeverity.HIGH.value,
                score_contribution=0.0,
                description="Resolved event",
                resolution_status=FrictionResolution.RESOLVED.value,
            )
            pg_session.add(ev)
        await pg_session.commit()

        repo = FrictionRepository(pg_session)
        engine = FrictionScoreEngine(repo)
        snapshot = await engine.compute_score(workspace_id)

        assert snapshot.score == 0.0, \
            f"B26: Resolved events must NOT count toward BFS, got {snapshot.score}"

    async def test_b26_workspace_isolation(self, pg_session: AsyncSession):
        """
        Friction events from workspace B MUST NOT affect workspace A's score.
        """
        workspace_a = uuid.uuid4()
        workspace_b = uuid.uuid4()
        # 10 events in workspace B
        await self._insert_friction_events(
            pg_session, workspace_b,
            FrictionType.LEAD_RESPONSE_DELAY.value, 10
        )
        await pg_session.commit()

        repo = FrictionRepository(pg_session)
        engine = FrictionScoreEngine(repo)
        snapshot = await engine.compute_score(workspace_a)

        assert snapshot.score == 0.0, \
            f"B26: Workspace B events must not affect workspace A's BFS, got {snapshot.score}"


# ═════════════════════════════════════════════════════════════════════════════
# B27 — ROI Calculation
# ═════════════════════════════════════════════════════════════════════════════

class TestB27ROICalculation:
    """
    B27 CERTIFICATION: ROICalculator must correctly convert operational metrics
    into financial values using the documented formulas. Verified against
    real FinancialConfig from the database.
    """

    def test_b27_time_savings_formula(self):
        """
        TIME_SAVINGS formula: financial_value = (minutes_saved / 60) × hourly_cost
        With 120 minutes saved and hourly_cost=100:
          = (120/60) × 100 = 200.0
        """
        config = FinancialConfig(
            workspace_id=uuid.uuid4(),
            average_hourly_cost=100.0,
            average_deal_value=10000.0,
            conversion_rate=0.10,
        )
        result = ROICalculator.calculate_financial_value(
            category=ImpactCategory.TIME_SAVINGS,
            raw_value=120.0,   # 120 minutes saved
            config=config,
        )
        assert result == pytest.approx(200.0), \
            f"B27: Expected 200.0 for 120 min @ $100/hr, got {result}"

    def test_b27_revenue_protection_formula(self):
        """
        REVENUE_PROTECTION: financial_value = raw_value (direct pass-through).
        """
        config = FinancialConfig(
            workspace_id=uuid.uuid4(),
            average_hourly_cost=50.0,
            average_deal_value=5000.0,
            conversion_rate=0.20,
        )
        result = ROICalculator.calculate_financial_value(
            category=ImpactCategory.REVENUE_PROTECTION,
            raw_value=7500.0,
            config=config,
        )
        assert result == pytest.approx(7500.0), \
            f"B27: REVENUE_PROTECTION should be direct pass-through, got {result}"

    def test_b27_opportunity_recovery_formula(self):
        """
        OPPORTUNITY_RECOVERY: financial_value = opportunities × deal_value × conversion_rate
        With 3 recovered opportunities, deal_value=10000, conversion_rate=0.10:
          = 3 × 10000 × 0.10 = 3000.0
        """
        config = FinancialConfig(
            workspace_id=uuid.uuid4(),
            average_hourly_cost=50.0,
            average_deal_value=10000.0,
            conversion_rate=0.10,
        )
        result = ROICalculator.calculate_financial_value(
            category=ImpactCategory.OPPORTUNITY_RECOVERY,
            raw_value=3.0,   # 3 opportunities recovered
            config=config,
        )
        assert result == pytest.approx(3000.0), \
            f"B27: Expected 3000.0 for 3 opportunities, got {result}"

    def test_b27_cost_reduction_formula(self):
        """
        COST_REDUCTION: financial_value = raw_value (direct cost reduction).
        """
        config = FinancialConfig(
            workspace_id=uuid.uuid4(),
            average_hourly_cost=50.0,
            average_deal_value=5000.0,
            conversion_rate=0.10,
        )
        result = ROICalculator.calculate_financial_value(
            category=ImpactCategory.COST_REDUCTION,
            raw_value=1250.0,
            config=config,
        )
        assert result == pytest.approx(1250.0), \
            f"B27: COST_REDUCTION should be direct pass-through, got {result}"

    def test_b27_unknown_category_returns_zero(self):
        """
        Unrecognized categories must return 0.0 — not crash.
        """
        config = FinancialConfig(
            workspace_id=uuid.uuid4(),
            average_hourly_cost=50.0,
            average_deal_value=5000.0,
            conversion_rate=0.10,
        )
        result = ROICalculator.calculate_financial_value(
            category=ImpactCategory.STRATEGIC,   # Not in ROI formulas
            raw_value=1000.0,
            config=config,
        )
        assert result == pytest.approx(0.0), \
            f"B27: Unknown category must return 0.0, got {result}"

    async def test_b27_financial_config_persisted_and_retrieved(self, pg_session: AsyncSession):
        """
        FinancialConfig must be persisted to and retrieved from real PostgreSQL
        with all float values intact.
        """
        workspace_id = uuid.uuid4()
        config = FinancialConfig(
            workspace_id=workspace_id,
            average_hourly_cost=75.0,
            average_deal_value=25000.0,
            conversion_rate=0.15,
        )
        pg_session.add(config)
        await pg_session.commit()

        # Retrieve via ImpactRepository
        repo = ImpactRepository(pg_session)
        retrieved = await repo.get_financial_config(workspace_id)

        assert retrieved is not None, "B27: FinancialConfig not retrieved from DB"
        assert retrieved.average_hourly_cost == pytest.approx(75.0)
        assert retrieved.average_deal_value == pytest.approx(25000.0)
        assert retrieved.conversion_rate == pytest.approx(0.15)

    async def test_b27_value_attribution_persisted(self, pg_session: AsyncSession):
        """
        ValueAttribution (ROI evidence) must persist to real PostgreSQL
        and be retrievable for the period query.
        """
        workspace_id = uuid.uuid4()
        repo = ImpactRepository(pg_session)

        # Create an ImpactEvent
        ev = ImpactEvent(
            workspace_id=workspace_id,
            event_type="lead_recovered",
            source_feature="FollowUpEngine",
            payload={"lead_id": str(uuid.uuid4())},
        )
        pg_session.add(ev)
        await pg_session.flush()

        # Create attribution
        attribution = ValueAttribution(
            event_id=ev.id,
            workspace_id=workspace_id,
            category=ImpactCategory.OPPORTUNITY_RECOVERY,
            raw_metric_name="opportunities_recovered",
            raw_metric_value=2.0,
            estimated_financial_value=2000.0,
            confidence_score=0.85,
        )
        pg_session.add(attribution)
        await pg_session.commit()

        # Query for the period
        now = datetime.now(timezone.utc)
        attributions = await repo.get_attributions_for_period(
            workspace_id,
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
        )

        assert len(attributions) >= 1, \
            "B27: ValueAttribution must be retrievable from real PostgreSQL"
        found = next((a for a in attributions if a.workspace_id == workspace_id), None)
        assert found is not None
        assert found.estimated_financial_value == pytest.approx(2000.0)
        assert found.confidence_score == pytest.approx(0.85)
