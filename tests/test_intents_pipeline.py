"""
HunterOS Engage V1 - Comprehensive Test Suite for Intent Intelligence (Phase 2.3.1)
Covers taxonomy, rule packs, recognition/validation/resolution separation, 6-stage pipeline,
evidence graphs, provenance, views, CQRS queries, public API v1, and REST endpoints.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.domain.conversations.analysis.models import (
    AnalysisDiagnostics,
    ArtifactProvenance,
    CanonicalValue,
    ConversationAnalysisResult,
    ConversationMetadata,
    ExtractedFact,
    FactCategory,
    SourceMessageRef,
    TopicAnalysis,
    TopicDistribution,
)
from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ActionOwnerType,
    ConversationInsightResult,
    InsightCategory,
    InsightDiagnostics,
    InsightEvidence,
    InsightMetadata,
    OpportunityInsight,
    RiskInsight,
)
from app.domain.conversations.timeline.models import (
    ConversationEventStream,
    ConversationTimeline,
    ImportantMoment,
    ImportantMomentType,
    MilestoneType,
    TimelineEvent,
    TimelineEventCategory,
    TimelineEventType,
    TimelineMetadata,
    TimelineMilestone,
    TimelineProvenance,
    TimelineScopeType,
)
from app.domain.intents.api import intent_api_v1, IntentDetectionAPIv1
from app.domain.intents.context import IntentDetectionContext, IntentPipelineState
from app.domain.intents.engine import IntentDetectionEngine
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    EvidenceNodeType,
    IntentDetectionMethod,
    IntentDetectionResult,
    IntentEvidence,
    IntentTaxonomyCategory,
    IntentType,
)
from app.domain.intents.query import IntentQueryEngine
from app.domain.intents.recognizer import IntentRecognizer
from app.domain.intents.repository import InMemoryIntentRepository
from app.domain.intents.resolver import IntentResolver
from app.domain.intents.rules.packs.core import CoreRulePack
from app.domain.intents.rules.packs.healthcare import HealthcareRulePack
from app.domain.intents.rules.packs.manufacturing import ManufacturingRulePack
from app.domain.intents.rules.packs.real_estate import RealEstateRulePack
from app.domain.intents.rules.registry import IntentRulePackRegistry
from app.domain.intents.taxonomy import IntentTaxonomy
from app.domain.intents.validation import IntentValidator
from app.domain.intents.views.registry import IntentViewRegistry
from app.domain.intents.views.standard import (
    AuditIntentView,
    ExecutiveIntentView,
    OperationsIntentView,
    SalesIntentView,
)
from app.main import create_app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_workspace_id():
    return uuid.uuid4()


@pytest.fixture
def sample_conversation_id():
    return "conv-test-intent-101"


@pytest.fixture
def sample_customer_id():
    return "cust-test-intent-888"


@pytest.fixture
def mock_conversation_intelligence_artifacts(
    sample_conversation_id, sample_workspace_id, sample_customer_id
):
    now = datetime.now(timezone.utc)
    ev_prov = TimelineProvenance(analysis_id=uuid.uuid4(), source_message_ids=["msg-1", "msg-2"])

    # 1. Timeline Events
    events = [
        TimelineEvent(
            event_id=uuid.uuid4(),
            conversation_id=sample_conversation_id,
            workspace_id=sample_workspace_id,
            occurred_at=now,
            event_type=TimelineEventType.CUSTOMER_INTRODUCED,
            category=TimelineEventCategory.COMMUNICATION,
            title="Customer Introduced",
            description="Hi, I am looking for a 3 BHK luxury apartment in downtown.",
            provenance=ev_prov,
        ),
        TimelineEvent(
            event_id=uuid.uuid4(),
            conversation_id=sample_conversation_id,
            workspace_id=sample_workspace_id,
            occurred_at=now,
            event_type=TimelineEventType.REQUIREMENT_IDENTIFIED,
            category=TimelineEventCategory.REQUIREMENT,
            title="Requirement: 3 BHK",
            description="Need 3 BHK with sea view and 2 car parking spaces.",
            provenance=ev_prov,
        ),
        TimelineEvent(
            event_id=uuid.uuid4(),
            conversation_id=sample_conversation_id,
            workspace_id=sample_workspace_id,
            occurred_at=now,
            event_type=TimelineEventType.BUDGET_MENTIONED,
            category=TimelineEventCategory.FINANCIAL,
            title="Budget Discussed",
            description="Budget range discussed: between $1.2M and $1.5M.",
            provenance=ev_prov,
        ),
        TimelineEvent(
            event_id=uuid.uuid4(),
            conversation_id=sample_conversation_id,
            workspace_id=sample_workspace_id,
            occurred_at=now,
            event_type=TimelineEventType.MEETING_SCHEDULED,
            category=TimelineEventCategory.SCHEDULING,
            title="Site Visit Scheduled",
            description="Scheduled site visit walkthrough for this Saturday at 11 AM.",
            provenance=ev_prov,
        ),
        TimelineEvent(
            event_id=uuid.uuid4(),
            conversation_id=sample_conversation_id,
            workspace_id=sample_workspace_id,
            occurred_at=now,
            event_type=TimelineEventType.DOCUMENT_SHARED,
            category=TimelineEventCategory.DOCUMENT,
            title="Document Requested",
            description="Please email the floor plans, brochure, and payment schedule.",
            provenance=ev_prov,
        ),
    ]

    milestones = [
        TimelineMilestone(
            milestone_id=uuid.uuid4(),
            milestone_type=MilestoneType.BUDGET_ESTABLISHED,
            title="Budget Established",
            description="Confirmed budget limit of $1.5M.",
            timestamp=now,
            source_event_ids=[events[2].event_id],
        )
    ]

    moments = [
        ImportantMoment(
            moment_id=uuid.uuid4(),
            moment_type=ImportantMomentType.FIRST_REQUIREMENT,
            title="Expressed High Booking Interest",
            significance="Customer eager to block unit if floor plan approved",
            timestamp=now,
            source_event_id=events[1].event_id,
        )
    ]

    stream = ConversationEventStream(
        stream_id=uuid.uuid4(),
        conversation_id=sample_conversation_id,
        workspace_id=sample_workspace_id,
        customer_id=sample_customer_id,
        events=events,
        start_time=now,
        end_time=now,
    )

    t_meta = TimelineMetadata(
        timeline_id=uuid.uuid4(),
        conversation_id=sample_conversation_id,
        workspace_id=sample_workspace_id,
        customer_id=sample_customer_id,
        scope_type=TimelineScopeType.CONVERSATION,
        total_events=len(events),
        total_milestones=len(milestones),
        total_moments=len(moments),
        start_time=now,
        end_time=now,
        duration_seconds=120.0,
        event_category_distribution={"COMMUNICATION": 1, "REQUIREMENT": 1, "FINANCIAL": 1, "SCHEDULING": 1, "DOCUMENT": 1},
    )

    timeline = ConversationTimeline(
        timeline_id=t_meta.timeline_id,
        conversation_id=sample_conversation_id,
        workspace_id=sample_workspace_id,
        customer_id=sample_customer_id,
        scope_type=TimelineScopeType.CONVERSATION,
        metadata=t_meta,
        event_stream=stream,
        milestones=milestones,
        important_moments=moments,
    )

    # 2. Analysis Result
    facts = [
        ExtractedFact(
            fact_id=uuid.uuid4(),
            category=FactCategory.PROPERTY_REFERENCE,
            key="property_type",
            raw_value="3 BHK downtown",
            canonical_value=CanonicalValue(
                raw_value="3 BHK downtown",
                normalized_value="3 BHK downtown",
                data_type="string",
            ),
            provenance=ArtifactProvenance(
                pipeline_stage="EXTRACTING_FACTS",
                source_messages=[SourceMessageRef(message_id="msg-1")],
            ),
        ),
        ExtractedFact(
            fact_id=uuid.uuid4(),
            category=FactCategory.BUDGET_REFERENCE,
            key="budget_limit",
            raw_value="$1.5M",
            canonical_value=CanonicalValue(
                raw_value="$1.5M",
                normalized_value=1500000,
                data_type="currency",
                unit="USD",
            ),
            provenance=ArtifactProvenance(
                pipeline_stage="EXTRACTING_FACTS",
                source_messages=[SourceMessageRef(message_id="msg-2")],
            ),
        ),
    ]

    topics = TopicAnalysis(
        primary_topic="Property Requirements",
        primary_taxonomy_path="Commercial > Property",
        provenance=ArtifactProvenance(pipeline_stage="DETECTING_TOPICS"),
        distribution=[
            TopicDistribution(
                topic_name="Floor Plans",
                taxonomy_path="Commercial > Layout",
                category="Property",
                frequency=2,
                weight=0.5,
                provenance=ArtifactProvenance(pipeline_stage="DETECTING_TOPICS"),
            )
        ],
    )

    analysis = ConversationAnalysisResult(
        analysis_id=uuid.uuid4(),
        conversation_id=sample_conversation_id,
        workspace_id=sample_workspace_id,
        analyzed_at=now,
        metadata=ConversationMetadata(conversation_id=sample_conversation_id),
        facts=facts,
        topics=topics,
        diagnostics=AnalysisDiagnostics(),
    )

    # 3. Insight Result
    actions = [
        ActionItemInsight(
            action_id=uuid.uuid4(),
            category=InsightCategory.REQUESTED_DOCUMENT,
            owner_type=ActionOwnerType.INTERNAL_TEAM,
            title="Send floor plan brochure PDF",
            description="Send 3 BHK brochure and payment plan to customer",
            evidence=InsightEvidence(source_message_ids=["msg-1"]),
        )
    ]

    insights = ConversationInsightResult(
        insight_result_id=uuid.uuid4(),
        conversation_id=sample_conversation_id,
        workspace_id=sample_workspace_id,
        metadata=InsightMetadata(
            insight_result_id=uuid.uuid4(),
            conversation_id=sample_conversation_id,
            workspace_id=sample_workspace_id,
            customer_id=sample_customer_id,
            total_insights=1,
            total_risks=0,
            total_opportunities=0,
            total_action_items=1,
        ),
        action_items=actions,
        diagnostics=InsightDiagnostics(),
    )

    return analysis, timeline, insights


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_intent_taxonomy_hierarchy():
    """Verify taxonomy structure, category mapping, paths, and tree generation."""
    # Check all categories exist
    assert IntentTaxonomyCategory.COMMERCIAL == "Commercial"
    assert IntentTaxonomyCategory.OPERATIONAL == "Operational"
    assert IntentTaxonomyCategory.RELATIONSHIP == "Relationship"
    assert IntentTaxonomyCategory.INFORMATION == "Information"

    # Check node lookups
    prop_node = IntentTaxonomy.get_node(IntentType.PROPERTY_INQUIRY)
    assert prop_node.category == IntentTaxonomyCategory.COMMERCIAL
    assert "property_inquiry" in prop_node.taxonomy_path

    doc_node = IntentTaxonomy.get_node(IntentType.DOCUMENT_REQUEST)
    assert doc_node.category == IntentTaxonomyCategory.OPERATIONAL
    assert "document_request" in doc_node.taxonomy_path

    ref_node = IntentTaxonomy.get_node(IntentType.REFERRAL)
    assert ref_node.category == IntentTaxonomyCategory.RELATIONSHIP

    tree = IntentTaxonomy.get_taxonomy_tree()
    assert "Commercial" in tree
    assert "Operational" in tree
    assert "Relationship" in tree
    assert "Information" in tree


def test_rule_packs_and_registry():
    """Verify modular rule packs (Core, RealEstate, Healthcare, Manufacturing) and thread-safe registry."""
    registry = IntentRulePackRegistry(register_defaults=False)
    assert len(registry.list_packs()) == 0

    core_pack = CoreRulePack()
    re_pack = RealEstateRulePack()
    health_pack = HealthcareRulePack()
    mfg_pack = ManufacturingRulePack()

    registry.register_pack(core_pack)
    registry.register_pack(re_pack)
    registry.register_pack(health_pack)
    registry.register_pack(mfg_pack)

    assert len(registry.list_packs()) == 4
    assert registry.get_pack("CoreRulePack") is not None
    assert registry.get_pack("RealEstateRulePack") is not None

    all_rules = registry.get_all_rules()
    assert len(all_rules) >= (len(core_pack.get_rules()) + len(re_pack.get_rules()))


def test_separated_architecture_flow(mock_conversation_intelligence_artifacts, sample_conversation_id, sample_workspace_id):
    """
    Verify strict separation:
    IntentRecognizer -> CandidateIntents -> IntentValidator -> IntentResolver -> IntentDetectionResult
    """
    analysis, timeline, insights = mock_conversation_intelligence_artifacts

    context = IntentDetectionContext(
        analysis_result=analysis,
        timeline=timeline,
        insight_result=insights,
        conversation_id=sample_conversation_id,
        workspace_id=sample_workspace_id,
    )

    # 1. Recognition Phase
    recognizer = IntentRecognizer()
    candidates, rule_report = recognizer.recognize(context)
    assert len(candidates) > 0
    assert len(rule_report.executed_rules) > 0
    assert len(rule_report.matched_rules) > 0

    # 2. Validation Phase
    validator = IntentValidator()
    context.candidate_intents = candidates
    validated = []
    for cand in candidates:
        errs = validator.validate_candidate(cand, context)
        assert len(errs) == 0  # Should be clean
        validated.append(cand)
    assert len(validated) == len(candidates)

    # 3. Resolution Phase
    resolver = IntentResolver()
    resolved, conflicts = resolver.resolve(validated)
    assert len(resolved) <= len(validated)
    assert len(resolved) > 0

    # Ensure highest confidence candidate survived and evidence graphs merged
    types_found = {i.intent_type for i in resolved}
    assert IntentType.PROPERTY_INQUIRY in types_found
    assert IntentType.BUDGET_DISCUSSION in types_found
    assert IntentType.SCHEDULE_SITE_VISIT in types_found
    assert IntentType.DOCUMENT_REQUEST in types_found


def test_full_6_stage_pipeline(mock_conversation_intelligence_artifacts, sample_conversation_id, sample_workspace_id, sample_customer_id):
    """Verify complete 6-stage pipeline execution with diagnostics, timings, and metadata."""
    analysis, timeline, insights = mock_conversation_intelligence_artifacts

    engine = IntentDetectionEngine()
    result = engine.detect_intents(
        analysis_result=analysis,
        timeline=timeline,
        insight_result=insights,
        conversation_id=sample_conversation_id,
        workspace_id=sample_workspace_id,
        customer_id=sample_customer_id,
    )

    assert isinstance(result, IntentDetectionResult)
    assert result.conversation_id == sample_conversation_id
    assert result.workspace_id == sample_workspace_id
    assert result.customer_id == sample_customer_id
    assert len(result.intents) > 0

    # Diagnostics verification
    diag = result.diagnostics
    assert diag.is_valid is True
    assert diag.pipeline_execution_time_ms >= 0.0
    assert "RecognizeCandidatesStage" in diag.stage_timings_ms
    assert "ValidateEvidenceStage" in diag.stage_timings_ms
    assert "ResolveDuplicatesStage" in diag.stage_timings_ms
    assert len(diag.stages_executed) >= 6
    assert diag.rule_report.execution_time_ms >= 0.0

    # Metadata verification
    meta = result.metadata
    assert meta.total_intents == len(result.intents)
    assert meta.dominant_category in (IntentTaxonomyCategory.COMMERCIAL, IntentTaxonomyCategory.OPERATIONAL)
    assert meta.average_confidence > 0.8


def test_evidence_graph_and_provenance(mock_conversation_intelligence_artifacts):
    """Verify evidence graph structure and lineage provenance tracking."""
    analysis, timeline, insights = mock_conversation_intelligence_artifacts
    engine = IntentDetectionEngine()
    result = engine.detect_intents(analysis, timeline, insights)

    for intent in result.intents:
        # Provenance verification
        assert intent.provenance.intent_version == "1.0.0"
        assert intent.provenance.detector_version == "1.0.0"
        assert intent.provenance.rule_version == "1.0.0"
        assert intent.provenance.rule_pack_name in ("CoreRulePack", "RealEstateRulePack")
        assert len(intent.provenance.rule_name) > 0

        # Evidence completeness verification
        ev = intent.supporting_evidence
        assert ev.has_sufficient_evidence is True
        assert ev.confidence_score > 0.0

        # Evidence graph verification
        if ev.evidence_graph:
            assert len(ev.evidence_graph.nodes) > 0
            assert len(ev.evidence_graph.edges) > 0
            node_types = {n.node_type for n in ev.evidence_graph.nodes}
            assert any(nt in node_types for nt in (EvidenceNodeType.MESSAGE, EvidenceNodeType.FACT, EvidenceNodeType.TIMELINE_EVENT))


def test_architectural_boundary_guardrails(mock_conversation_intelligence_artifacts, sample_conversation_id, sample_workspace_id):
    """Verify zero memory mutations, zero journey updates, and rejection of forbidden metadata keys."""
    analysis, timeline, insights = mock_conversation_intelligence_artifacts
    context = IntentDetectionContext(
        analysis_result=analysis,
        timeline=timeline,
        insight_result=insights,
        conversation_id=sample_conversation_id,
        workspace_id=sample_workspace_id,
    )

    validator = IntentValidator()

    # Create an invalid intent containing forbidden keys
    invalid_intent = DetectedIntent(
        intent_id=uuid.uuid4(),
        conversation_id=sample_conversation_id,
        workspace_id=sample_workspace_id,
        intent_type=IntentType.PROPERTY_INQUIRY,
        taxonomy_category=IntentTaxonomyCategory.COMMERCIAL,
        taxonomy_path="Commercial > Property Inquiry",
        business_importance=BusinessImportance.COMMERCIAL,
        title="Invalid Intent",
        description="Contains forbidden predictive mutations",
        confidence=0.9,
        detection_method=IntentDetectionMethod.RULE_BASED,
        supporting_evidence=IntentEvidence(
            source_message_ids=["msg-1"],
            confidence_score=0.9,
        ),
        metadata={
            "sentiment": "positive",
            "lead_score": 95,
            "journey_stage_mutation": "Stage_3",
            "recommendation": "Call immediately",
        },
    )

    errors = validator.validate_candidate(invalid_intent, context)
    assert len(errors) >= 4
    assert any("sentiment" in err for err in errors)
    assert any("lead_score" in err for err in errors)
    assert any("journey_stage_mutation" in err for err in errors)
    assert any("recommendation" in err for err in errors)


def test_multi_perspective_views(mock_conversation_intelligence_artifacts):
    """Verify Executive, Sales, Operations, and Audit views."""
    analysis, timeline, insights = mock_conversation_intelligence_artifacts
    engine = IntentDetectionEngine()
    result = engine.detect_intents(analysis, timeline, insights)

    views = IntentViewRegistry()

    # 1. Executive View
    exec_view = views.get_view("executive")
    assert exec_view is not None
    exec_data = exec_view.render(result)
    assert exec_data["view"] == "executive"
    assert "total_intents_detected" in exec_data
    assert "key_objectives" in exec_data

    # 2. Sales View
    sales_view = views.get_view("sales")
    sales_data = sales_view.render(result)
    assert sales_data["view"] == "sales"
    assert "commercial_intents" in sales_data
    assert "booking_interest_detected" in sales_data

    # 3. Operations View
    ops_view = views.get_view("operations")
    ops_data = ops_view.render(result)
    assert ops_data["view"] == "operations"
    assert "document_requests" in ops_data

    # 4. Audit View
    audit_view = views.get_view("audit")
    audit_data = audit_view.render(result)
    assert audit_data["view"] == "audit"
    assert "diagnostics" in audit_data
    assert "intents" in audit_data


def test_cqrs_repository_and_query_engine(mock_conversation_intelligence_artifacts, sample_conversation_id, sample_workspace_id):
    """Verify repository storage and read-side query engine."""
    analysis, timeline, insights = mock_conversation_intelligence_artifacts
    repo = InMemoryIntentRepository()
    engine = IntentDetectionEngine(repository=repo)

    result = engine.detect_intents(analysis, timeline, insights)

    query_engine = IntentQueryEngine(repository=repo)

    # By conversation
    fetched = query_engine.get_conversation_intents(sample_conversation_id)
    assert fetched is not None
    assert fetched.detection_id == result.detection_id

    # Query with filters
    comm_intents = query_engine.query(
        conversation_id=sample_conversation_id,
        category=IntentTaxonomyCategory.COMMERCIAL,
    )
    assert len(comm_intents) > 0
    assert all(i.taxonomy_category == IntentTaxonomyCategory.COMMERCIAL for i in comm_intents)

    # Render view through query engine
    rendered = query_engine.render_view(sample_conversation_id, "sales")
    assert rendered is not None
    assert rendered["view"] == "sales"


def test_frozen_public_api_v1(mock_conversation_intelligence_artifacts, sample_conversation_id):
    """Verify IntentDetectionAPIv1 frozen public contract."""
    analysis, timeline, insights = mock_conversation_intelligence_artifacts

    result = intent_api_v1.detect_intents(analysis, timeline, insights)
    assert result is not None

    conv_result = intent_api_v1.get_conversation_intents(sample_conversation_id)
    assert conv_result is not None

    sales_view = intent_api_v1.render_view(sample_conversation_id, "sales")
    assert sales_view is not None

    tree = intent_api_v1.get_taxonomy_tree()
    assert isinstance(tree, dict)
    assert "Commercial" in tree


def test_fastapi_rest_endpoints(mock_conversation_intelligence_artifacts, sample_conversation_id):
    """Verify FastAPI router endpoints for Intent Intelligence."""
    analysis, timeline, insights = mock_conversation_intelligence_artifacts
    intent_api_v1.detect_intents(analysis, timeline, insights)

    app = create_app()
    client = TestClient(app)

    # GET taxonomy
    resp = client.get("/api/v1/intents/taxonomy")
    assert resp.status_code == 200
    assert "Commercial" in resp.json()

    # GET rule packs
    resp = client.get("/api/v1/intents/rules/packs")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2

    # GET conversation intents
    resp = client.get(f"/api/v1/intents/{sample_conversation_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == sample_conversation_id
    assert len(data["intents"]) > 0

    # GET perspective view
    resp = client.get(f"/api/v1/intents/{sample_conversation_id}/views/executive")
    assert resp.status_code == 200
    assert resp.json()["view"] == "executive"

    # GET evidence graph
    resp = client.get(f"/api/v1/intents/{sample_conversation_id}/evidence-graph")
    assert resp.status_code == 200
    assert "nodes" in resp.json()
    assert "edges" in resp.json()

    # GET query
    resp = client.get(f"/api/v1/intents?conversation_id={sample_conversation_id}&category=Commercial")
    assert resp.status_code == 200
    assert len(resp.json()) > 0
