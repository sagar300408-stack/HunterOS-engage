"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.3: Maturity Engine & Query Engine Integration Tests
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from app.domain.journey.definitions.core import (
    build_sales_journey_definition,
    register_core_definitions,
)
from app.domain.journey.definitions.registry import (
    JourneyDefinitionRegistry,
    StageDefinitionRegistry,
)
from app.domain.journey.maturity.configuration import (
    JourneyMaturityConfigurationRegistry,
    build_sales_maturity_configuration,
)
from app.domain.journey.maturity.engine import JourneyMaturityEngine
from app.domain.journey.maturity.models import (
    JourneyHealthState,
    JourneyMaturityLevel,
    JourneyMaturityResult,
)
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
from app.domain.journey.repository import InMemoryJourneyRepository


@pytest.fixture
def test_setup():
    stage_reg = StageDefinitionRegistry()
    defn_reg = JourneyDefinitionRegistry()
    register_core_definitions(defn_reg, stage_reg)

    config_reg = JourneyMaturityConfigurationRegistry()
    config_reg.register(build_sales_maturity_configuration())

    journey_repo = InMemoryJourneyRepository()
    maturity_repo = InMemoryJourneyMaturityRepository()

    engine = JourneyMaturityEngine(
        journey_repo=journey_repo,
        maturity_repo=maturity_repo,
        journey_registry=defn_reg,
        config_registry=config_reg,
    )
    query_engine = JourneyMaturityQueryEngine(
        repository=maturity_repo,
    )

    return {
        "journey_repo": journey_repo,
        "maturity_repo": maturity_repo,
        "engine": engine,
        "query_engine": query_engine,
        "defn_reg": defn_reg,
    }


def test_maturity_engine_assessment_pipeline(test_setup):
    journey_repo = test_setup["journey_repo"]
    engine = test_setup["engine"]
    defn_reg = test_setup["defn_reg"]

    sales_defn = defn_reg.get_by_type(JourneyType.SALES)
    assert sales_defn is not None

    # Setup journey state in repo
    journey_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    state = JourneyState(
        journey_instance_id=journey_id,
        workspace_id="ws-engine-test",
        entity_type="CUSTOMER",
        entity_id="cust-201",
        journey_definition_id=sales_defn.journey_id,
        journey_definition_version="1.0.0",
        current_stage=JourneyStageCode.QUALIFIED,
        status=JourneyStatus.ACTIVE,
        stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED, JourneyStageCode.QUALIFIED],
        journey_started_at=now - timedelta(days=12),
        stage_entered_at=now - timedelta(days=2),
    )
    journey_repo.save_journey_state(state)

    # Append transitions
    t1 = JourneyStageTransition(
        transition_id=uuid.uuid4(),
        journey_instance_id=journey_id,
        from_stage=JourneyStageCode.NEW_LEAD,
        to_stage=JourneyStageCode.INTERESTED,
        transition_type=TransitionType.ADVANCE,
        confidence=0.9,
        evidence=[
            JourneyEvidence(
                evidence_id=uuid.uuid4(),
                evidence_type=EvidenceType.INTENT,
                source_id="msg-1",
                confidence=0.9,
            )
        ],
        occurred_at=now - timedelta(days=8),
    )
    t2 = JourneyStageTransition(
        transition_id=uuid.uuid4(),
        journey_instance_id=journey_id,
        from_stage=JourneyStageCode.INTERESTED,
        to_stage=JourneyStageCode.QUALIFIED,
        transition_type=TransitionType.ADVANCE,
        confidence=0.85,
        evidence=[
            JourneyEvidence(
                evidence_id=uuid.uuid4(),
                evidence_type=EvidenceType.INTENT,
                source_id="msg-2",
                confidence=0.85,
            )
        ],
        occurred_at=now - timedelta(days=2),
    )
    journey_repo.append_transition(journey_id, t1)
    journey_repo.append_transition(journey_id, t2)

    # Run comprehensive assessment
    result = engine.calculate_maturity(journey_id)

    assert isinstance(result, JourneyMaturityResult)
    assert result.journey_id == journey_id
    assert result.current_stage == JourneyStageCode.QUALIFIED
    assert result.maturity.maturity_score > 0.0
    assert result.maturity.maturity_level in (JourneyMaturityLevel.QUALIFIED, JourneyMaturityLevel.ADVANCED, JourneyMaturityLevel.DEVELOPING)
    assert len(result.stage_residency) == 3
    assert result.velocity is not None
    assert result.stability is not None
    assert result.momentum is not None
    assert result.health is not None
    assert result.provenance is not None
    assert result.provenance.calculation_method == "DETERMINISTIC_11_STAGE_PIPELINE"
    assert result.diagnostics.total_execution_time_ms >= 0.0


def test_maturity_query_engine_queries(test_setup):
    journey_repo = test_setup["journey_repo"]
    maturity_repo = test_setup["maturity_repo"]
    engine = test_setup["engine"]
    query_engine = test_setup["query_engine"]
    defn_reg = test_setup["defn_reg"]

    sales_defn = defn_reg.get_by_type(JourneyType.SALES)
    ws_id = "ws-summary-test"
    now = datetime.now(timezone.utc)

    # Create and assess multiple journeys
    for i in range(4):
        j_id = uuid.uuid4()
        stage = JourneyStageCode.QUALIFIED if i % 2 == 0 else JourneyStageCode.NEW_LEAD
        state = JourneyState(
            journey_instance_id=j_id,
            workspace_id=ws_id,
            entity_type="CUSTOMER",
            entity_id=f"cust-{i}",
            journey_definition_id=sales_defn.journey_id,
            journey_definition_version="1.0.0",
            current_stage=stage,
            status=JourneyStatus.ACTIVE,
            stage_history=[JourneyStageCode.NEW_LEAD, stage] if stage != JourneyStageCode.NEW_LEAD else [stage],
            journey_started_at=now - timedelta(days=5),
            stage_entered_at=now - timedelta(days=2),
        )
        journey_repo.save_journey_state(state)
        engine.calculate_maturity(j_id, workspace_id=ws_id)

    # Query latest maturity result
    results = maturity_repo.query_maturity(workspace_id=ws_id)
    assert len(results) == 4

    # Query specific journey metrics through Query Engine
    first_j_id = results[0].journey_id
    score = query_engine.get_maturity_score(first_j_id)
    assert score is not None
    level = query_engine.get_maturity_level(first_j_id)
    assert level is not None
    health = query_engine.get_health(first_j_id)
    assert health is not None
