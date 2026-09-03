"""
BW4 Certification Test — B18 (Recommendation Relevance & Decision Trace Auditability)

Tests run against real PostgreSQL.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone

# ── Bootstrap SQLAlchemy mapper order ─────────────────────────────────────────
from app.domain.customers.models import Customer  # noqa: F401 — must be first
from app.domain.conversations.models import Conversation  # noqa: F401
from app.domain.insight.models import InsightSnapshot, InsightCategory, InsightSeverity, InsightImpact, InsightLifecycle
from app.domain.insight.repository import InsightRepository
from app.domain.recommendation.models import RecommendationSnapshot, RecommendationLifecycle
from app.domain.recommendation.repository import RecommendationRepository
from app.domain.recommendation.engine import RecommendationEngine
from app.domain.recommendation.bootstrap import bootstrap_recommendations


@pytest_asyncio.fixture
async def pg_session_rec(pg_engine):
    from app.domain.conversations.models import Base
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.mark.asyncio
async def test_b18_recommendation_generation_and_persistence(pg_session_rec):
    """
    B18 Recommendation Relevance:
    Given a customer with an active performance decline insight regarding engagement,
    RecommendationEngine must generate an evidence-backed RecommendationSnapshot
    with calculated relevance score, suggested actions, and decision trace linking to the insight.
    """
    session = pg_session_rec
    workspace_id = uuid.uuid4()
    target_id = uuid.uuid4()
    target_type = "customer"

    bootstrap_recommendations()

    # 1. Insert an active insight indicating declining customer engagement
    insight_repo = InsightRepository(session)
    insight = InsightSnapshot(
        workspace_id=workspace_id,
        target_type=target_type,
        target_id=target_id,
        title="Customer Engagement Dropping",
        summary="Reply rate dropped below 20% across recent communications.",
        category=InsightCategory.PERFORMANCE_DECLINE.value,
        severity=InsightSeverity.HIGH.value,
        impact=InsightImpact.HIGH.value,
        lifecycle_status=InsightLifecycle.ACTIVE.value,
        confidence=0.90,
        related_health_objects=["customer_engagement_health"],
        related_kpis=["reply_rate"],
        evidence_graph={"trend": "downward"},
        generator_name="EngagementDeclineInsightGenerator",
        generator_version="1.0",
        trigger_source="kpi_evaluator",
    )
    await insight_repo.save_insight(insight)

    # 2. Execute RecommendationEngine
    rec_engine = RecommendationEngine(session)
    recs = await rec_engine.generate_recommendations(
        workspace_id=workspace_id,
        target_type=target_type,
        target_id=target_id,
    )

    assert len(recs) >= 1, "Expected at least 1 recommendation to be generated"
    rec = recs[0]

    # Verify recommendation relevance and structure
    assert rec.target_type == target_type
    assert rec.target_id == target_id
    assert rec.workspace_id == workspace_id
    assert rec.recommendation_score >= 70.0, f"Expected high relevance score, got {rec.recommendation_score}"
    assert rec.confidence >= 0.80
    assert rec.lifecycle_status == RecommendationLifecycle.ACTIVE.value
    assert len(rec.suggested_actions) >= 1
    assert "suggested_cadence_id" in str(rec.suggested_actions)

    # Verify decision trace provenance link
    assert rec.decision_trace is not None
    assert str(insight.id) in rec.decision_trace.get("insight_ids", [])

    # 3. Verify PostgreSQL read-model retrieval
    rec_repo = RecommendationRepository(session)
    active_recs = await rec_repo.get_latest_recommendations(target_type, target_id)
    assert len(active_recs) >= 1
    assert active_recs[0].id == rec.id


@pytest.mark.asyncio
async def test_b18_recommendation_workspace_isolation(pg_session_rec):
    """
    B18 Multi-Tenant Workspace Isolation:
    Recommendations generated for Workspace A must never be visible to Workspace B.
    """
    session = pg_session_rec
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()
    target_id_a = uuid.uuid4()
    target_id_b = uuid.uuid4()

    bootstrap_recommendations()

    insight_repo = InsightRepository(session)
    rec_engine = RecommendationEngine(session)
    rec_repo = RecommendationRepository(session)

    # Create insight in Workspace A
    insight_a = InsightSnapshot(
        workspace_id=ws_a,
        target_type="customer",
        target_id=target_id_a,
        title="Customer Engagement Dropping",
        summary="Reply rate dropped.",
        category=InsightCategory.PERFORMANCE_DECLINE.value,
        severity=InsightSeverity.NORMAL.value,
        impact=InsightImpact.MEDIUM.value,
        lifecycle_status=InsightLifecycle.ACTIVE.value,
        confidence=0.85,
        related_health_objects=["customer_engagement_health"],
        related_kpis=[],
        evidence_graph={},
        generator_name="EngagementDeclineInsightGenerator",
        generator_version="1.0",
        trigger_source="kpi_evaluator",
    )
    await insight_repo.save_insight(insight_a)

    recs_a = await rec_engine.generate_recommendations(ws_a, "customer", target_id_a)
    assert len(recs_a) >= 1

    # Query Workspace B for target_id_b
    recs_b = await rec_repo.get_latest_recommendations("customer", target_id_b)
    assert len(recs_b) == 0, "Workspace B should have 0 recommendations"

    # Verify query by generator for Workspace B target returns None
    active_b = await rec_repo.get_active_recommendation_by_generator(
        "customer", target_id_b, recs_a[0].generator_name
    )
    assert active_b is None
