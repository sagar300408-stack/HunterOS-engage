"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: API & Router Endpoint Tests
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from starlette.testclient import TestClient
from fastapi import FastAPI

from app.domain.journey.api import JourneyIntelligenceAPIv1, journey_api_v1
from app.domain.journey.definitions.core import (
    build_sales_journey_definition,
    register_core_definitions,
)
from app.domain.journey.definitions.registry import (
    JourneyDefinitionRegistry,
    StageDefinitionRegistry,
    default_journey_registry,
    default_stage_registry,
)
from app.domain.journey.engine import JourneyIntelligenceEngine, default_journey_engine
from app.domain.journey.maturity.configuration import (
    JourneyMaturityConfigurationRegistry,
    build_sales_maturity_configuration,
)
from app.domain.journey.maturity.engine import JourneyMaturityEngine
from app.domain.journey.maturity.models import JourneyMaturityLevel
from app.domain.journey.maturity.query import JourneyMaturityQueryEngine
from app.domain.journey.maturity.repository import InMemoryJourneyMaturityRepository
from app.domain.journey.models import (
    EvidenceType,
    JourneyEvidence,
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
    JourneyStatus,
    JourneyType,
    TransitionType,
)
from app.domain.journey.repository import InMemoryJourneyRepository, default_journey_repository
from app.domain.journey.router import router as journey_router


@pytest.fixture
def api_test_setup():
    stage_reg = StageDefinitionRegistry()
    defn_reg = JourneyDefinitionRegistry()
    register_core_definitions(defn_reg, stage_reg)

    config_reg = JourneyMaturityConfigurationRegistry()
    config_reg.register(build_sales_maturity_configuration())

    journey_repo = InMemoryJourneyRepository()
    maturity_repo = InMemoryJourneyMaturityRepository()

    engine = JourneyIntelligenceEngine(
        read_repository=journey_repo,
        write_repository=journey_repo,
        journey_registry=defn_reg,
        stage_registry=stage_reg,
    )
    mat_engine = JourneyMaturityEngine(
        journey_repo=journey_repo,
        maturity_repo=maturity_repo,
        journey_registry=defn_reg,
        config_registry=config_reg,
    )
    mat_query = JourneyMaturityQueryEngine(
        repository=maturity_repo,
    )

    api = JourneyIntelligenceAPIv1(
        engine=engine,
        maturity_engine=mat_engine,
        maturity_query_engine=mat_query,
    )

    # FastAPI app for testing router
    app = FastAPI()
    app.include_router(journey_router)
    client = TestClient(app)

    return {
        "api": api,
        "journey_repo": journey_repo,
        "maturity_repo": maturity_repo,
        "defn_reg": defn_reg,
        "client": client,
    }


def test_api_maturity_methods(api_test_setup):
    api = api_test_setup["api"]
    repo = api_test_setup["journey_repo"]
    defn_reg = api_test_setup["defn_reg"]

    sales_defn = defn_reg.get_by_type(JourneyType.SALES)
    journey_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    state = JourneyState(
        journey_instance_id=journey_id,
        workspace_id="ws-api-test",
        entity_type="CUSTOMER",
        entity_id="cust-301",
        journey_definition_id=sales_defn.journey_id,
        journey_definition_version="1.0.0",
        current_stage=JourneyStageCode.QUALIFIED,
        status=JourneyStatus.ACTIVE,
        stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED],
        journey_started_at=now - timedelta(days=10),
        stage_entered_at=now - timedelta(days=3),
    )
    repo.save_journey_state(state)

    # 1. Test API calculate_maturity
    maturity_res = api.calculate_maturity(journey_id)
    assert maturity_res.journey_id == journey_id
    assert maturity_res.maturity.maturity_score > 0.0
    assert maturity_res.maturity.maturity_level in (
        JourneyMaturityLevel.INITIAL,
        JourneyMaturityLevel.EARLY,
        JourneyMaturityLevel.DEVELOPING,
        JourneyMaturityLevel.QUALIFIED,
        JourneyMaturityLevel.ADVANCED,
    )

    # 2. Test API get_stage_residency
    residencies = api.get_stage_residency(journey_id)
    assert len(residencies) >= 1

    # 3. Test API get_health
    health = api.get_health(journey_id)
    assert health is not None

    # 4. Test API get_momentum & stability
    momentum = api.get_momentum(journey_id)
    assert momentum is not None
    stability = api.get_stability(journey_id)
    assert stability is not None

    # 5. Test API views with maturity included
    exec_view = api.get_executive_view(journey_id, include_maturity=True)
    assert exec_view is not None
    assert "maturity_score" in exec_view
    assert "maturity_level" in exec_view

    sales_view = api.get_sales_view(journey_id, include_maturity=True)
    assert sales_view is not None
    assert "maturity_score" in sales_view
    assert "maturity_level" in sales_view


def test_router_maturity_endpoints(api_test_setup):
    client = api_test_setup["client"]
    default_journey_engine.bootstrap()

    sales_defn = default_journey_registry.get_by_type(JourneyType.SALES)
    journey_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    state = JourneyState(
        journey_instance_id=journey_id,
        workspace_id=uuid.uuid4(),
        entity_type="CUSTOMER",
        entity_id="cust-401",
        journey_definition_id=sales_defn.journey_id,
        journey_definition_version="1.0.0",
        current_stage=JourneyStageCode.QUALIFIED,
        status=JourneyStatus.ACTIVE,
        stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.QUALIFIED],
        journey_started_at=now - timedelta(days=10),
        stage_entered_at=now - timedelta(days=3),
    )
    # Put state in default repo consumed by global router singleton
    default_journey_repository.save_journey_state(state)

    # 1. GET maturity
    resp = client.get(f"/api/v1/journeys/{journey_id}/maturity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["journey_id"] == str(journey_id)
    assert "maturity" in data
    assert "stage_residency" in data
    assert "health" in data

    # 2. GET momentum
    resp = client.get(f"/api/v1/journeys/{journey_id}/momentum")
    assert resp.status_code == 200
    mom = resp.json()
    assert "state" in mom
    assert "momentum_score" in mom

    # 3. GET stability
    resp = client.get(f"/api/v1/journeys/{journey_id}/stability")
    assert resp.status_code == 200
    stab = resp.json()
    assert "stability_score" in stab
    assert "stability_level" in stab

    # 4. GET residency
    resp = client.get(f"/api/v1/journeys/{journey_id}/residency")
    assert resp.status_code == 200
    res_data = resp.json()
    assert "residencies" in res_data
    assert len(res_data["residencies"]) >= 1

    # 5. GET health
    resp = client.get(f"/api/v1/journeys/{journey_id}/health")
    assert resp.status_code == 200
    health_data = resp.json()
    assert "state" in health_data
    assert "summary" in health_data
