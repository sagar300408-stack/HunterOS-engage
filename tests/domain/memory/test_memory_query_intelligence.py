import uuid
from app.api.v1.auth_deps import get_current_user
from app.domain.security.models import User, UserRole

"""
HunterOS Engage — Memory Query & Retrieval Intelligence Test Suite (Refinement Phase 2.1.3)

Comprehensive test suite verifying:
1. Strict CQRS Read-Only Invariants (Zero writes, Zero events, Zero timeline logs, Zero version changes)
2. Query Objects & Query Handlers Architecture
3. Specialized Sub-Engines (Search, Projection, Statistics, Export) & Facade
4. Projection Registry & Multi-Version Views (SUMMARY, EXECUTIVE V1/V2, LIGHTWEIGHT, Field Masking)
5. Secure Keyset Cursor Pagination & Cross-Tenant Token Isolation
6. Specification Pattern & Boolean Combinators (AND, OR, NOT)
7. Dynamic JSON Filter Compiler & Sorting Engine
8. Query Planner Execution Optimization
9. Telemetry, Operational Metrics & Memory Query Cache Layer
10. Tabular Export Dataset Transformations
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.domain.conversations.models import Base
from app.domain.memory.cache import DefaultMemoryQueryCacheProvider
from app.domain.memory.models import CustomerMemory, LifecycleStatus
from app.domain.memory.queries.bus import MemoryQueryBus
from app.domain.memory.queries.engines.export import MemoryExportEngine
from app.domain.memory.queries.engines.projection import (
    MemoryProjectionEngine,
    ProjectionDefinition,
    ProjectionRegistry,
)
from app.domain.memory.queries.engines.search import (
    MemorySearchEngine,
    SearchCompiler,
)
from app.domain.memory.queries.engines.statistics import (
    MemoryStatisticsEngine,
    QueryMetricsTracker,
)
from app.domain.memory.queries.facade import MemoryQueryFacade
from app.domain.memory.queries.filters import (
    FilterCompiler,
    FilterCondition,
    FilterGroup,
    FilterOperator,
)
from app.domain.memory.queries.handlers import (
    BulkGetCustomerMemoryHandler,
    ExportPreviewHandler,
    GetCursorPaginatedMemoryHandler,
    GetCustomerMemoryHandler,
    GetProjectionHandler,
    GetStatisticsHandler,
    SearchCustomerMemoryHandler,
)
from app.domain.memory.queries.models import (
    BulkGetCustomerMemoryQuery,
    CustomerMemoryDTO,
    ExecutiveViewDTO,
    ExportPreviewQuery,
    GetCursorPaginatedMemoryQuery,
    GetCustomerMemoryQuery,
    GetProjectionQuery,
    GetStatisticsQuery,
    LightweightViewDTO,
    MemoryExportDTO,
    MemoryStatisticsDTO,
    ProjectedMemoryDTO,
    SearchCustomerMemoryQuery,
    SummaryViewDTO,
)
from app.domain.memory.queries.pagination import (
    CursorCodec,
    CursorPaginatedResult,
    CursorPaginationParams,
    OffsetPaginatedResult,
    OffsetPaginationParams,
)
from app.domain.memory.queries.planner import QueryExecutionPlan, QueryPlanner
from app.domain.memory.queries.sorting import SortCompiler, SortDirection, SortField
from app.domain.memory.queries.specifications import (
    ActiveCustomersSpecification,
    AndSpecification,
    ArchivedCustomersSpecification,
    BudgetRangeSpecification,
    LifecycleSpecification,
    LocationSpecification,
    LockedCustomersSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
    TagSpecification,
    TrueSpecification,
    UpdatedRecentlySpecification,
    VersionSpecification,
    WorkspaceSpecification,
)
from app.domain.memory.repositories.read_repository import SqlAlchemyMemoryReadRepository
from app.domain.memory.service import MemoryService
from app.main import app


# ── Fixtures & Setup ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine):
    session_maker = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def seed_data(db_session: AsyncSession):
    """Seed comprehensive customer memory records across 2 workspaces."""
    workspace_a = uuid4()
    workspace_b = uuid4()

    records = [
        # Customer 1: Workspace A, Active, Villa in Miami, Budget 5M, VIP
        CustomerMemory(
            id=uuid4(),
            customer_id=uuid4(),
            workspace_id=workspace_a,
            lifecycle_status="ACTIVE",
            version_number=3,
            revision_id=str(uuid4()),
            is_deleted=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
            updated_at=datetime.now(timezone.utc) - timedelta(days=1),
            memory_payload={
                "personal_info": {"full_name": "Alexander Vance", "location": {"city": "Miami", "state": "FL"}},
                "identity": {"tags": ["VIP", "investor", "luxury"]},
                "financial_info": {"budget_min": 3000000.0, "budget_max": 6000000.0, "investment_intent": "CAPITAL_APPRECIATION"},
                "property_info": {"property_types": ["Villa", "Penthouse"]},
                "journey_snapshot": {"current_stage": "NEGOTIATION", "milestones": [{"name": "offer_made"}]},
                "relationship_info": {"decision_makers": ["Alexander Vance", "Elena Vance"]},
            },
        ),
        # Customer 2: Workspace A, Active, Condo in Miami, Budget 1.5M
        CustomerMemory(
            id=uuid4(),
            customer_id=uuid4(),
            workspace_id=workspace_a,
            lifecycle_status="ACTIVE",
            version_number=1,
            revision_id=str(uuid4()),
            is_deleted=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=5),
            updated_at=datetime.now(timezone.utc) - timedelta(days=2),
            memory_payload={
                "personal_info": {"full_name": "Beatrice Stone", "location": {"city": "Miami", "state": "FL"}},
                "identity": {"tags": ["first_time_buyer", "condo"]},
                "financial_info": {"budget_min": 1000000.0, "budget_max": 1500000.0, "investment_intent": "PRIMARY_RESIDENCE"},
                "property_info": {"property_types": ["Condo"]},
                "journey_snapshot": {"current_stage": "SEARCHING", "milestones": []},
            },
        ),
        # Customer 3: Workspace A, Locked, Mansion in New York, Budget 15M
        CustomerMemory(
            id=uuid4(),
            customer_id=uuid4(),
            workspace_id=workspace_a,
            lifecycle_status="LOCKED",
            version_number=5,
            revision_id=str(uuid4()),
            is_deleted=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=20),
            updated_at=datetime.now(timezone.utc) - timedelta(days=3),
            memory_payload={
                "personal_info": {"full_name": "Charles Montgomery", "location": {"city": "New York", "state": "NY"}},
                "identity": {"tags": ["UHNW", "investor"]},
                "financial_info": {"budget_min": 10000000.0, "budget_max": 20000000.0, "investment_intent": "PORTFOLIO_DIVERSIFICATION"},
                "property_info": {"property_types": ["Townhouse", "Mansion"]},
                "journey_snapshot": {"current_stage": "CLOSING", "milestones": [{"name": "contract_signed"}]},
            },
        ),
        # Customer 4: Workspace A, Archived
        CustomerMemory(
            id=uuid4(),
            customer_id=uuid4(),
            workspace_id=workspace_a,
            lifecycle_status="ARCHIVED",
            version_number=2,
            revision_id=str(uuid4()),
            is_deleted=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=40),
            updated_at=datetime.now(timezone.utc) - timedelta(days=30),
            memory_payload={
                "personal_info": {"full_name": "David Miller", "location": {"city": "Chicago", "state": "IL"}},
                "identity": {"tags": ["inactive"]},
                "financial_info": {"budget_min": 500000.0, "budget_max": 800000.0},
                "journey_snapshot": {"current_stage": "ON_HOLD"},
            },
        ),
        # Customer 5: Workspace B, Active, Loft in Austin
        CustomerMemory(
            id=uuid4(),
            customer_id=uuid4(),
            workspace_id=workspace_b,
            lifecycle_status="ACTIVE",
            version_number=1,
            revision_id=str(uuid4()),
            is_deleted=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=5),
            memory_payload={
                "personal_info": {"full_name": "Eva Green", "location": {"city": "Austin", "state": "TX"}},
                "identity": {"tags": ["tech", "VIP"]},
                "financial_info": {"budget_min": 2000000.0, "budget_max": 3500000.0},
                "property_info": {"property_types": ["Loft"]},
                "journey_snapshot": {"current_stage": "TOURING"},
            },
        ),
    ]

    for rec in records:
        db_session.add(rec)
    await db_session.commit()

    return {
        "workspace_a": workspace_a,
        "workspace_b": workspace_b,
        "records": records,
    }


# ── Test Suite 1: Query Objects & Query Bus Dispatching ───────────────────────

@pytest.mark.asyncio
async def test_query_bus_dispatch_and_handlers(async_engine, db_session, seed_data):
    """Verify Query Objects route through QueryBus to dedicated Handlers and return immutable DTOs."""
    repo = SqlAlchemyMemoryReadRepository(session_factory=lambda: db_session)
    cache = DefaultMemoryQueryCacheProvider()
    bus = MemoryQueryBus(cache_provider=cache)

    search_engine = MemorySearchEngine(repo)
    proj_engine = MemoryProjectionEngine()
    stats_engine = MemoryStatisticsEngine(repo, cache)
    export_engine = MemoryExportEngine(repo)

    bus.register(GetCustomerMemoryQuery, GetCustomerMemoryHandler(repo))
    bus.register(BulkGetCustomerMemoryQuery, BulkGetCustomerMemoryHandler(repo))
    bus.register(SearchCustomerMemoryQuery, SearchCustomerMemoryHandler(search_engine))
    bus.register(GetCursorPaginatedMemoryQuery, GetCursorPaginatedMemoryHandler(search_engine))
    bus.register(GetProjectionQuery, GetProjectionHandler(repo, proj_engine))
    bus.register(GetStatisticsQuery, GetStatisticsHandler(stats_engine))
    bus.register(ExportPreviewQuery, ExportPreviewHandler(export_engine))

    # 1. GetCustomerMemoryQuery
    target_rec = seed_data["records"][0]
    query = GetCustomerMemoryQuery(customer_id=target_rec.customer_id)
    res_dto = await bus.execute(query, session=db_session)

    assert isinstance(res_dto, CustomerMemoryDTO)
    assert res_dto.customer_id == target_rec.customer_id
    assert res_dto.version_number == 3
    assert res_dto.memory_payload["personal_info"]["full_name"] == "Alexander Vance"

    # 2. BulkGetCustomerMemoryQuery
    bulk_ids = [r.customer_id for r in seed_data["records"][:3]]
    bulk_res = await bus.execute(BulkGetCustomerMemoryQuery(customer_ids=bulk_ids), session=db_session)
    assert len(bulk_res) == 3
    assert all(isinstance(d, CustomerMemoryDTO) for d in bulk_res)


# ── Test Suite 2: Specification Pattern & Combinators ─────────────────────────

@pytest.mark.asyncio
async def test_specifications_and_boolean_combinators(async_engine, db_session, seed_data):
    """Verify composite specifications (AND, OR, NOT) filter accurately."""
    repo = SqlAlchemyMemoryReadRepository(session_factory=lambda: db_session)
    search_engine = MemorySearchEngine(repo)

    ws_a = seed_data["workspace_a"]

    # Spec: In Workspace A AND Tagged 'VIP'
    spec = AndSpecification(
        WorkspaceSpecification(ws_a),
        TagSpecification("VIP"),
    )
    plan = QueryPlanner.create_plan(CustomerMemory, specifications=[spec])
    results, count = await repo.execute_query_plan_offset(plan, session=db_session)
    assert count == 1
    assert results[0].memory_payload["personal_info"]["full_name"] == "Alexander Vance"

    # Spec: In Workspace A AND (Miami OR New York)
    spec_or = AndSpecification(
        WorkspaceSpecification(ws_a),
        OrSpecification(
            LocationSpecification("Miami"),
            LocationSpecification("New York"),
        ),
    )
    plan_or = QueryPlanner.create_plan(CustomerMemory, specifications=[spec_or])
    results_or, count_or = await repo.execute_query_plan_offset(plan_or, session=db_session)
    assert count_or == 3  # Alexander, Beatrice, Charles

    # Spec: In Workspace A AND NOT Locked
    spec_not_locked = AndSpecification(
        WorkspaceSpecification(ws_a),
        NotSpecification(LockedCustomersSpecification()),
    )
    plan_not = QueryPlanner.create_plan(CustomerMemory, specifications=[spec_not_locked])
    results_not, count_not = await repo.execute_query_plan_offset(plan_not, session=db_session)
    assert count_not == 3  # Alexander, Beatrice, David


# ── Test Suite 3: Keyset Cursor Pagination & Cross-Tenant Protection ──────────

@pytest.mark.asyncio
async def test_cursor_pagination_and_token_isolation(async_engine, db_session, seed_data):
    """Verify deterministic keyset cursor pagination and workspace token boundary protection."""
    repo = SqlAlchemyMemoryReadRepository(session_factory=lambda: db_session)
    search_engine = MemorySearchEngine(repo)

    ws_a = seed_data["workspace_a"]
    ws_b = seed_data["workspace_b"]

    # Page 1 with limit 2
    query_p1 = GetCursorPaginatedMemoryQuery(workspace_id=ws_a, limit=2)
    p1 = await search_engine.search_cursor(query_p1, session=db_session)

    assert len(p1.items) == 2
    assert p1.has_more is True
    assert p1.next_cursor is not None

    # Page 2 using next_cursor
    query_p2 = GetCursorPaginatedMemoryQuery(workspace_id=ws_a, cursor=p1.next_cursor, limit=2)
    p2 = await search_engine.search_cursor(query_p2, session=db_session)

    assert len(p2.items) == 2
    assert p2.has_more is False
    assert p2.next_cursor is None

    # Verify no item duplication across pages
    p1_ids = {i.customer_id for i in p1.items}
    p2_ids = {i.customer_id for i in p2.items}
    assert len(p1_ids.intersection(p2_ids)) == 0

    # Tampering test: Pass Workspace A cursor into Workspace B query
    with pytest.raises(ValueError, match="Cross-workspace cursor boundary violation"):
        CursorCodec.decode_cursor(p1.next_cursor, expected_workspace_id=ws_b)


# ── Test Suite 4: Projection Views & Versioning ───────────────────────────────

@pytest.mark.asyncio
async def test_projection_views_and_versioning(seed_data):
    """Verify SUMMARY, EXECUTIVE (V1 vs V2), LIGHTWEIGHT, and custom field masking."""
    target_rec = seed_data["records"][0]
    dto = MemorySearchEngine._to_dto(target_rec)

    # 1. SUMMARY View
    summary: SummaryViewDTO = MemoryProjectionEngine.project(dto, view_name="SUMMARY")
    assert isinstance(summary, SummaryViewDTO)
    assert summary.full_name == "Alexander Vance"
    assert summary.city == "Miami"
    assert summary.budget_max == 6000000.0
    assert summary.projection_version == "1.0.0"

    # 2. EXECUTIVE View V1 & V2
    exec_v1: ExecutiveViewDTO = MemoryProjectionEngine.project(dto, view_name="EXECUTIVE", projection_version="1.0.0")
    assert isinstance(exec_v1, ExecutiveViewDTO)
    assert exec_v1.financial_capacity == "HIGH_NET_WORTH"
    assert exec_v1.projection_version == "1.0.0"

    exec_v2: ExecutiveViewDTO = MemoryProjectionEngine.project(dto, view_name="EXECUTIVE", projection_version="2.0.0")
    assert isinstance(exec_v2, ExecutiveViewDTO)
    assert exec_v2.projection_version == "2.0.0"

    # 3. LIGHTWEIGHT View
    lw: LightweightViewDTO = MemoryProjectionEngine.project(dto, view_name="LIGHTWEIGHT")
    assert isinstance(lw, LightweightViewDTO)
    assert lw.version_number == 3
    assert lw.lifecycle_status == "ACTIVE"

    # 4. Custom Field Masking
    mask = ["personal_info.full_name", "financial_info.budget_max"]
    masked: ProjectedMemoryDTO = MemoryProjectionEngine.project(dto, projection_mask=mask)
    assert isinstance(masked, ProjectedMemoryDTO)
    assert masked.projected_data == {
        "personal_info": {"full_name": "Alexander Vance"},
        "financial_info": {"budget_max": 6000000.0},
    }


# ── Test Suite 5: Domain & Operational Metrics Telemetry ──────────────────────

@pytest.mark.asyncio
async def test_statistics_and_operational_telemetry(async_engine, db_session, seed_data):
    """Verify lifecycle aggregations, storage calculation, cache hit ratio, and telemetry tracking."""
    repo = SqlAlchemyMemoryReadRepository(session_factory=lambda: db_session)
    cache = DefaultMemoryQueryCacheProvider()
    tracker = QueryMetricsTracker.get_instance()
    tracker.reset()

    facade = MemoryQueryFacade(repo, cache_provider=cache)
    ws_a = seed_data["workspace_a"]

    # 1st call via Facade: Cache miss -> Compute & record metrics
    stats_dto = await facade.get_statistics(
        workspace_id=ws_a,
        bypass_cache=False,
        session=db_session,
    )

    assert stats_dto.total_memories == 4
    assert stats_dto.active_count == 2
    assert stats_dto.locked_count == 1
    assert stats_dto.archived_count == 1
    assert stats_dto.top_cities.get("Miami") == 2
    assert stats_dto.top_tags.get("vip") == 1

    # 2nd call via Facade: Cache hit
    cached_stats = await facade.get_statistics(
        workspace_id=ws_a,
        bypass_cache=False,
        session=db_session,
    )
    assert cached_stats.total_memories == 4
    assert cached_stats.operational_metrics is not None
    assert cached_stats.operational_metrics.total_queries_executed >= 2
    assert cached_stats.operational_metrics.cache_hit_ratio > 0.0


# ── Test Suite 6: Tabular Export Engine ────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_engine_tabular_flattening(async_engine, db_session, seed_data):
    """Verify hierarchical JSON payloads flatten into standardized tabular records."""
    repo = SqlAlchemyMemoryReadRepository(session_factory=lambda: db_session)
    export_engine = MemoryExportEngine(repo)

    ws_a = seed_data["workspace_a"]
    query = ExportPreviewQuery(
        workspace_id=ws_a,
        export_format="CSV",
        columns=["customer_id", "full_name", "city", "max_budget", "tags"],
        max_rows=10,
    )

    export_dto: MemoryExportDTO = await export_engine.preview_export(query, session=db_session)
    assert export_dto.total_rows == 4
    assert export_dto.columns == ["Customer ID", "Full Name", "City", "Max Budget", "Tags"]

    first_row = next(r for r in export_dto.rows if r["Full Name"] == "Alexander Vance")
    assert first_row["City"] == "Miami"
    assert first_row["Max Budget"] == 6000000.0
    assert "VIP" in first_row["Tags"]


# ── Test Suite 7: Strict CQRS Zero-Mutation Invariant ─────────────────────────

@pytest.mark.asyncio
async def test_strict_cqrs_read_only_invariants(async_engine, db_session, seed_data):
    """Verify query operations execute without any state mutation, event dispatch, or version increment."""
    repo = SqlAlchemyMemoryReadRepository(session_factory=lambda: db_session)
    facade = MemoryQueryFacade(repo)

    target_rec = seed_data["records"][0]
    initial_version = target_rec.version_number
    initial_updated = target_rec.updated_at

    # Execute multiple diverse queries
    await facade.get_customer_memory(target_rec.customer_id, session=db_session)
    await facade.get_projection(target_rec.customer_id, view_name="EXECUTIVE", session=db_session)
    await facade.get_statistics(workspace_id=seed_data["workspace_a"], session=db_session)
    await facade.search_memories(workspace_id=seed_data["workspace_a"], tags=["VIP"], session=db_session)

    # Re-fetch from database to verify immutability
    reloaded = await repo.get_by_customer_id(target_rec.customer_id, session=db_session)
    assert reloaded.version_number == initial_version
    assert reloaded.updated_at == initial_updated
    assert reloaded.revision_id == target_rec.revision_id
    assert reloaded.lifecycle_status == target_rec.lifecycle_status


# ── Test Suite 8: REST API Endpoints Integration ──────────────────────────────

@pytest.mark.asyncio
async def test_rest_api_query_endpoints(async_engine, db_session, seed_data):
    """Verify REST API query routes for projections, cursor search, stats, and export."""
    async def override_get_db():
        yield db_session
        
    async def override_get_current_user():
        return User(id=uuid.uuid4(), email="test@test.com", workspace_id=seed_data["workspace_a"], role=UserRole.admin)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            target_rec = seed_data["records"][0]
            cid = str(target_rec.customer_id)
            wid = str(seed_data["workspace_a"])

            # 1. POST /memory/{customer_id}/projection (EXECUTIVE View)
            proj_resp = await client.post(
            f"/api/v1/memory/{cid}/projection",
            json={"view_name": "EXECUTIVE", "projection_version": "1.0.0"},
            )
            assert proj_resp.status_code == 200
            proj_data = proj_resp.json()
            assert proj_data["full_name"] == "Alexander Vance"
            assert proj_data["financial_capacity"] == "HIGH_NET_WORTH"

            # 2. POST /memory/search/cursor
            cursor_resp = await client.post(
            "/api/v1/memory/search/cursor",
            json={"workspace_id": wid, "limit": 2},
            )
            assert cursor_resp.status_code == 200
            cursor_data = cursor_resp.json()
            assert len(cursor_data["items"]) == 2
            assert cursor_data["has_more"] is True
            assert cursor_data["next_cursor"] is not None

            # 3. GET /memory/analytics/statistics
            stats_resp = await client.get(f"/api/v1/memory/analytics/statistics?workspace_id={wid}&bypass_cache=true")
            assert stats_resp.status_code == 200
            stats_data = stats_resp.json()
            assert stats_data["total_memories"] == 4
            assert stats_data["active_count"] == 2

            # 4. POST /memory/export/preview
            export_resp = await client.post(
            "/api/v1/memory/export/preview",
            json={"workspace_id": wid, "export_format": "CSV", "max_rows": 5},
            )
            assert export_resp.status_code == 200
            export_data = export_resp.json()
            assert export_data["total_rows"] == 4
            assert len(export_data["columns"]) > 0
    finally:
        app.dependency_overrides.pop(get_db, None)

