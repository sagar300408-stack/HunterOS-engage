"""
Unit tests for Resolution Views and Analytics calculations.
"""

from datetime import datetime, timezone
import uuid
import pytest

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import (
    DominanceFactor,
    DominantIntent,
    GraphSnapshot,
    IntentConflict,
    IntentConflictSeverity,
    IntentConflictType,
    IntentDependency,
    IntentDependencyType,
    IntentNode,
    IntentRelationship,
    IntentRelationshipType,
    IntentResolutionGraph,
    IntentResolutionGroup,
    MultiIntentResolutionResult,
    ResolutionDiagnostics,
    ResolutionMetadata,
    ResolutionProvenance,
    ResolutionStatus,
)
from app.domain.intents.resolution.schemas import MultiIntentResolutionResponse
from app.domain.intents.resolution.views.audit import AuditResolutionView
from app.domain.intents.resolution.views.executive import ExecutiveResolutionView
from app.domain.intents.resolution.views.operations import OperationsResolutionView
from app.domain.intents.resolution.views.sales import SalesResolutionView


def create_mock_resolution_result() -> MultiIntentResolutionResult:
    now = datetime.now(timezone.utc)
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    id3 = uuid.uuid4()

    n1 = IntentNode(
        intent_id=id1,
        canonical_name="Enterprise_Contract",
        category="COMMERCIAL",
        confidence=0.95,
        business_importance="CRITICAL",
    )
    n2 = IntentNode(
        intent_id=id2,
        canonical_name="Custom_Integration_Support",
        category="OPERATIONAL",
        confidence=0.90,
        business_importance="HIGH",
    )
    n3 = IntentNode(
        intent_id=id3,
        canonical_name="Security_Audit_Review",
        category="OPERATIONAL",
        confidence=0.85,
        business_importance="HIGH",
    )

    nodes = {str(id1): n1, str(id2): n2, str(id3): n3}

    rel = IntentRelationship(
        source_intent_id=id2,
        target_intent_id=id1,
        relationship_type=IntentRelationshipType.SUPPORTING,
        strength=0.8,
    )

    dep = IntentDependency(
        dependency_type=IntentDependencyType.REQUIRED,
        source_intent_id=id3,
        target_intent_id=id1,
        is_blocking=True,
        reason="Security audit must pass before enterprise contract",
    )

    conflict = IntentConflict(
        conflict_type=IntentConflictType.CONTRADICTING,
        severity=IntentConflictSeverity.MEDIUM,
        intent_ids=[id1, id2],
        description="Scope contradiction",
    )

    graph = IntentResolutionGraph(
        nodes=nodes,
        edges=[rel],
        dependencies=[dep],
        conflicts=[conflict],
    )

    dom = DominantIntent(
        intent_id=id1,
        canonical_name="Enterprise_Contract",
        dominance_score=0.95,
        primary_factor=DominanceFactor.BUSINESS_IMPORTANCE,
        supporting_intent_ids=[id2, id3],
    )

    group = IntentResolutionGroup(
        name="COMMERCIAL_Enterprise_Contract",
        group_type="COMMERCIAL",
        dominant_intent=dom,
        supporting_intents=[n2, n3],
        all_intent_ids=[id1, id2, id3],
        subgraph=graph,
        conflicts=[conflict],
        dependencies=[dep],
        resolution_status=ResolutionStatus.PARTIALLY_RESOLVED,
    )

    return MultiIntentResolutionResult(
        entity_type="CUSTOMER",
        entity_id="cust_999",
        workspace_id=uuid.uuid4(),
        conversation_id="conv_999",
        resolution_graph=graph,
        groups=[group],
        dominant_intents=[dom],
        snapshot=graph.create_snapshot(),
        metadata=ResolutionMetadata(
            entity_type="CUSTOMER",
            entity_id="cust_999",
            conversation_id="conv_999",
            total_input_intents=3,
            total_groups=1,
            total_relationships=1,
            total_conflicts=1,
            total_dependencies=1,
            total_dominant_intents=1,
        ),
        diagnostics=ResolutionDiagnostics(
            pipeline_execution_time_ms=5.2,
            stage_timings_ms={"Stage1": 1.0},
            stages_executed=["Stage1", "Stage2"],
            rules_evaluated=10,
            strategies_evaluated=4,
            is_valid=True,
        ),
        provenance=ResolutionProvenance(
            resolution_version="1.0.0",
            graph_version="1.0.0",
            rule_pack_version="1.0.0",
            pipeline_version="2.3.4",
            engine_version="1.0.0",
        ),
    )


def test_executive_view():
    result = create_mock_resolution_result()
    view = ExecutiveResolutionView().render(result)

    assert view["view_type"] == "EXECUTIVE"
    assert view["entity_id"] == "cust_999"
    assert "summary_metrics" in view
    assert view["summary_metrics"]["total_intents"] == 3
    assert len(view["dominant_intents"]) == 1


def test_sales_view():
    result = create_mock_resolution_result()
    view = SalesResolutionView().render(result)

    assert view["view_type"] == "SALES"
    assert view["total_commercial_intents"] >= 1
    assert len(view["purchasing_blockers"]) == 1
    assert "Security audit" in view["purchasing_blockers"][0]["reason"]


def test_operations_view():
    result = create_mock_resolution_result()
    view = OperationsResolutionView().render(result)

    assert view["view_type"] == "OPERATIONS"
    assert view["operational_intents_count"] == 2
    assert len(view["blocking_dependencies"]) == 1


def test_audit_view():
    result = create_mock_resolution_result()
    view = AuditResolutionView().render(result)

    assert view["view_type"] == "AUDIT"
    assert "provenance" in view
    assert "diagnostics" in view
    assert "snapshot" in view
    assert view["provenance"]["pipeline_version"] == "2.3.4"


def test_response_analytics_dto():
    result = create_mock_resolution_result()
    dto = MultiIntentResolutionResponse.from_domain(result)

    assert dto.analytics is not None
    assert dto.analytics.graph_connectivity >= 0.0
    assert dto.analytics.relationship_density >= 0.0
    assert dto.analytics.average_group_size == 3.0
    assert dto.analytics.dependency_chains_count == 1
    assert dto.analytics.intent_cohesion >= 0.0
