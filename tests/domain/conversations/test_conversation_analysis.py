"""
HunterOS Engage — Conversation Analysis Test Suite (Phase 2.2.1)

Exhaustive verification of:
1. Independent Pipeline Stages & Pipeline Runner
2. ConversationAnalysisContext & Telemetry
3. Extractors vs Engines Separation
4. AnalysisArtifactRegistry & SummaryTemplateRegistry
5. FactNormalizer Canonical Standardization
6. Hierarchical TopicTaxonomy & Path Resolution
7. Full Artifact Provenance & Lineage Traceability
8. CQRS Read/Write Repositories
9. Strict Architectural Boundaries (No Memory/Intent/Recommendation Mutations)
10. Frozen Public REST API v1
"""

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.conversations.analysis.context import (
    ConversationAnalysisContext,
)
from app.domain.conversations.analysis.engine import (
    ConversationAnalysisEngine,
    default_conversation_analysis_engine,
)
from app.domain.conversations.analysis.engines import (
    ConversationMetadataExtractor,
    ConversationSummaryEngine,
    KeyFactExtractionEngine,
    TopicDetectionEngine,
)
from app.domain.conversations.analysis.extractors.facts import (
    BudgetExtractor,
    CompanyInfoExtractor,
    ContactInfoExtractor,
    CustomerInfoExtractor,
    DateExtractor,
    DocumentMentionExtractor,
    LocationExtractor,
    ProductExtractor,
    PropertyExtractor,
)
from app.domain.conversations.analysis.extractors.summaries import (
    TemplateBasedSummaryGenerator,
)
from app.domain.conversations.analysis.extractors.topics import (
    TaxonomyTopicExtractor,
)
from app.domain.conversations.analysis.models import (
    ArtifactProvenance,
    CanonicalValue,
    ConversationAnalysisResult,
    ConversationMetadata,
    ConversationSegment,
    ConversationSummary,
    ExtractedFact,
    ExtractionMethod,
    FactCategory,
    MessageDirection,
    NormalizedMessage,
    PipelineState,
    SegmentType,
    SourceMessageRef,
    SummaryType,
    TopicAnalysis,
)
from app.domain.conversations.analysis.normalizer import FactNormalizer
from app.domain.conversations.analysis.pipeline import ConversationPipelineRunner
from app.domain.conversations.analysis.registry import (
    AnalysisArtifactDescriptor,
    AnalysisArtifactRegistry,
    ExecutiveSummaryTemplate,
    RealEstateSummaryTemplate,
    SummaryTemplateRegistry,
)
from app.domain.conversations.analysis.repository import (
    InMemoryConversationAnalysisReadRepository,
    InMemoryConversationAnalysisStorage,
    InMemoryConversationAnalysisWriteRepository,
)
from app.domain.conversations.analysis.segmentation import (
    ConversationSegmentationEngine,
)
from app.domain.conversations.analysis.stages import (
    FactExtractionStage,
    FactNormalizationStage,
    LoadStage,
    NormalizeStage,
    OutputStage,
    PipelineStage,
    SegmentStage,
    SummaryStage,
    TopicStage,
    ValidationStage,
)
from app.domain.conversations.analysis.taxonomy import (
    TopicTaxonomy,
    TopicTaxonomyNode,
)
from app.domain.conversations.analysis.validation import (
    AnalysisValidationFramework,
)


@pytest.fixture
def sample_conversation_messages():
    """Realistic multi-turn real estate customer conversation."""
    return [
        {
            "id": "msg_001",
            "sender": "customer",
            "content": "Hi there! My name is Rahul Sharma. I am looking for a 3 BHK apartment in Whitefield, Bangalore.",
            "timestamp": "2026-08-05T10:00:00Z",
            "direction": "INCOMING",
            "channel": "whatsapp",
        },
        {
            "id": "msg_002",
            "sender": "agent",
            "content": "Hello Rahul! Thanks for reaching out to Prestige Estates. We have fantastic 3 BHK units available around 1800 sqft.",
            "timestamp": "2026-08-05T10:01:30Z",
            "direction": "OUTGOING",
            "channel": "whatsapp",
        },
        {
            "id": "msg_003",
            "sender": "customer",
            "content": "My budget is ₹85 lakh. Can you offer any discount on the final price? Also, my email is rahul.sharma@example.com and phone is +91 98765 43210.",
            "timestamp": "2026-08-05T10:03:00Z",
            "direction": "INCOMING",
            "channel": "whatsapp",
        },
        {
            "id": "msg_004",
            "sender": "agent",
            "content": "We can offer a special 5% discount if booked this month. Let me send you the master_plan.pdf brochure.",
            "timestamp": "2026-08-05T10:04:15Z",
            "direction": "OUTGOING",
            "channel": "whatsapp",
        },
        {
            "id": "msg_005",
            "sender": "customer",
            "content": "Sounds great! Can we schedule a site visit for next Friday at 4:00 PM?",
            "timestamp": "2026-08-05T10:05:40Z",
            "direction": "INCOMING",
            "channel": "whatsapp",
        },
        {
            "id": "msg_006",
            "sender": "agent",
            "content": "Confirmed for next Friday at 4 PM. Thank you Rahul, see you then!",
            "timestamp": "2026-08-05T10:06:00Z",
            "direction": "OUTGOING",
            "channel": "whatsapp",
        },
    ]


# ── 1. Independent Pipeline Stages & Pipeline Runner ──────────────────────────

def test_independent_pipeline_stages(sample_conversation_messages):
    """Verify each pipeline stage runs independently and transforms context properly."""
    context = ConversationAnalysisContext(
        conversation_id="conv_test_001",
        raw_messages=sample_conversation_messages,
    )

    # 1. LoadStage
    load_stage = LoadStage()
    context = load_stage.run(context)
    assert context.state == PipelineState.LOADING
    assert "LoadStage" in context.diagnostics.stages_executed
    assert "LoadStage" in context.diagnostics.stage_timings_ms

    # 2. NormalizeStage
    norm_stage = NormalizeStage()
    context = norm_stage.run(context)
    assert context.state == PipelineState.NORMALIZING
    assert len(context.normalized_messages) == 6
    assert context.metadata is not None
    assert context.metadata.message_count == 6

    # 3. SegmentStage
    seg_stage = SegmentStage()
    context = seg_stage.run(context)
    assert context.state == PipelineState.SEGMENTING
    assert len(context.segments) >= 1

    # 4. TopicStage
    topic_stage = TopicStage()
    context = topic_stage.run(context)
    assert context.state == PipelineState.DETECTING_TOPICS
    assert context.topics is not None
    assert context.topics.primary_topic != ""

    # 5. FactExtractionStage
    fact_stage = FactExtractionStage()
    context = fact_stage.run(context)
    assert context.state == PipelineState.EXTRACTING_FACTS
    assert len(context.facts) > 0

    # 6. FactNormalizationStage
    norm_fact_stage = FactNormalizationStage()
    context = norm_fact_stage.run(context)
    assert context.state == PipelineState.NORMALIZING_FACTS
    # Find budget fact and verify canonical amount
    budget_facts = [f for f in context.facts if f.category == FactCategory.BUDGET_REFERENCE]
    assert len(budget_facts) >= 1
    assert budget_facts[0].canonical_value.normalized_value == 8500000
    assert budget_facts[0].canonical_value.unit == "INR"

    # 7. SummaryStage
    summary_stage = SummaryStage()
    context = summary_stage.run(context)
    assert context.state == PipelineState.SUMMARIZING
    assert "EXECUTIVE" in context.summaries
    assert "CUSTOMER" in context.summaries

    # 8. ValidationStage
    val_stage = ValidationStage()
    context = val_stage.run(context)
    assert context.state == PipelineState.VALIDATING
    assert context.diagnostics.is_valid is True

    # 9. OutputStage
    out_stage = OutputStage()
    context = out_stage.run(context)
    assert context.state == PipelineState.COMPLETED

    # Build result
    result = context.build_result()
    assert isinstance(result, ConversationAnalysisResult)
    assert result.conversation_id == "conv_test_001"
    assert result.diagnostics.is_valid is True


def test_pipeline_runner_custom_stage_insertion(sample_conversation_messages):
    """Verify PipelineRunner allows inserting and replacing custom stages."""
    class CustomAuditStage(PipelineStage):
        @property
        def stage_name(self) -> str:
            return "CustomAuditStage"
        @property
        def target_state(self) -> PipelineState:
            return PipelineState.VALIDATING
        def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
            context.set_artifact("audit_marker", "PASSED_CUSTOM_AUDIT")
            return context

    runner = ConversationPipelineRunner()
    runner.add_stage(CustomAuditStage(), index=8)  # Before OutputStage

    context = ConversationAnalysisContext(
        conversation_id="conv_custom_runner",
        raw_messages=sample_conversation_messages,
    )
    result = runner.execute(context)
    assert result.custom_artifacts.get("audit_marker") == "PASSED_CUSTOM_AUDIT"
    assert "CustomAuditStage" in result.diagnostics.stages_executed


# ── 2. Fact Normalizer Layer ──────────────────────────────────────────────────

def test_fact_normalizer_currencies():
    """Verify FactNormalizer converts various currency representations into canonical units."""
    normalizer = FactNormalizer()

    # Test Lakhs
    fact_lakh = ExtractedFact(
        category=FactCategory.BUDGET_REFERENCE,
        key="budget",
        raw_value="₹85 lakh",
        canonical_value=CanonicalValue(raw_value="₹85 lakh", normalized_value="₹85 lakh", data_type="currency"),
        provenance=ArtifactProvenance(pipeline_stage="test", confidence=1.0),
    )
    norm = normalizer.normalize(fact_lakh)
    assert norm.canonical_value.normalized_value == 8500000
    assert norm.canonical_value.unit == "INR"
    assert norm.canonical_value.formatted == "8,500,000 INR"

    # Test Crores
    fact_cr = ExtractedFact(
        category=FactCategory.BUDGET_REFERENCE,
        key="budget",
        raw_value="Rs. 1.25 Cr",
        canonical_value=CanonicalValue(raw_value="Rs. 1.25 Cr", normalized_value="Rs. 1.25 Cr", data_type="currency"),
        provenance=ArtifactProvenance(pipeline_stage="test", confidence=1.0),
    )
    norm_cr = normalizer.normalize(fact_cr)
    assert norm_cr.canonical_value.normalized_value == 12500000
    assert norm_cr.canonical_value.unit == "INR"

    # Test USD
    fact_usd = ExtractedFact(
        category=FactCategory.BUDGET_REFERENCE,
        key="budget",
        raw_value="$50,000",
        canonical_value=CanonicalValue(raw_value="$50,000", normalized_value="$50,000", data_type="currency"),
        provenance=ArtifactProvenance(pipeline_stage="test", confidence=1.0),
    )
    norm_usd = normalizer.normalize(fact_usd)
    assert norm_usd.canonical_value.normalized_value == 50000
    assert norm_usd.canonical_value.unit == "USD"

    # Test EUR with K
    fact_eur = ExtractedFact(
        category=FactCategory.BUDGET_REFERENCE,
        key="budget",
        raw_value="€200k",
        canonical_value=CanonicalValue(raw_value="€200k", normalized_value="€200k", data_type="currency"),
        provenance=ArtifactProvenance(pipeline_stage="test", confidence=1.0),
    )
    norm_eur = normalizer.normalize(fact_eur)
    assert norm_eur.canonical_value.normalized_value == 200000
    assert norm_eur.canonical_value.unit == "EUR"


def test_fact_normalizer_phones_and_emails():
    """Verify phone E.164 standardization and email normalization."""
    normalizer = FactNormalizer()

    # Phone 10-digits
    fact_phone = ExtractedFact(
        category=FactCategory.CONTACT_INFO,
        key="phone",
        raw_value="9876543210",
        canonical_value=CanonicalValue(raw_value="9876543210", normalized_value="9876543210", data_type="phone"),
        provenance=ArtifactProvenance(pipeline_stage="test", confidence=1.0),
    )
    norm_p = normalizer.normalize(fact_phone)
    assert norm_p.canonical_value.formatted == "+919876543210"

    # Email
    fact_email = ExtractedFact(
        category=FactCategory.CONTACT_INFO,
        key="email",
        raw_value="  USER.Test@Example.COM ",
        canonical_value=CanonicalValue(raw_value="USER.Test@Example.COM", normalized_value="", data_type="email"),
        provenance=ArtifactProvenance(pipeline_stage="test", confidence=1.0),
    )
    norm_e = normalizer.normalize(fact_email)
    assert norm_e.canonical_value.normalized_value == "user.test@example.com"


# ── 3. Hierarchical Topic Taxonomy ────────────────────────────────────────────

def test_topic_taxonomy_hierarchy_and_matching():
    """Verify TopicTaxonomy resolves hierarchical paths (Sales -> Pricing -> Discount)."""
    taxonomy = TopicTaxonomy()

    # Query node
    discount_node = taxonomy.get_node("sales/pricing/discount")
    assert discount_node is not None
    assert discount_node.name == "Discount"
    assert discount_node.category == "Sales"
    assert "discount" in discount_node.keywords

    # Match text
    text = "We are requesting a concession or discount on the quoted price."
    matches = taxonomy.match_all(text)
    assert len(matches) > 0
    matched_paths = [m[0].path for m in matches]
    assert "sales/pricing/discount" in matched_paths or "sales/pricing" in matched_paths

    # Custom node registration
    custom_node = TopicTaxonomyNode(
        name="Penthouse Luxury",
        path="real_estate/property/penthouse_luxury",
        category="Real Estate",
        keywords=["penthouse luxury", "sky villa"],
    )
    taxonomy.register_node(custom_node)
    retrieved = taxonomy.get_node("real_estate/property/penthouse_luxury")
    assert retrieved is not None
    assert retrieved.name == "Penthouse Luxury"


# ── 4. Registries & Summary Templates ─────────────────────────────────────────

def test_artifact_and_summary_registries():
    """Verify AnalysisArtifactRegistry and SummaryTemplateRegistry."""
    art_reg = AnalysisArtifactRegistry()
    assert art_reg.get("TOPIC_ANALYSIS") is not None
    assert len(art_reg.list_descriptors()) >= 5

    # Register custom descriptor
    art_reg.register(
        AnalysisArtifactDescriptor(
            name="SENTIMENT_PLACEHOLDER",
            category="CUSTOM",
            description="Custom descriptor test",
            is_custom=True,
        )
    )
    assert art_reg.get("SENTIMENT_PLACEHOLDER") is not None

    # Summary templates
    tpl_reg = SummaryTemplateRegistry()
    exec_tpl = tpl_reg.get(SummaryType.EXECUTIVE)
    assert exec_tpl is not None
    assert isinstance(exec_tpl, ExecutiveSummaryTemplate)

    re_tpl = tpl_reg.get("REAL_ESTATE_SPECIALIZED")
    assert re_tpl is not None
    assert isinstance(re_tpl, RealEstateSummaryTemplate)


# ── 5. Full Provenance & Lineage Tracking ─────────────────────────────────────

def test_artifact_provenance_integrity(sample_conversation_messages):
    """Verify every extracted artifact contains full provenance and lineage."""
    engine = ConversationAnalysisEngine()
    result = engine.analyze_conversation(
        conversation_id="conv_prov_test",
        raw_messages=sample_conversation_messages,
    )

    # Topics Provenance
    assert result.topics.provenance.pipeline_stage == "TopicStage"
    assert 0.0 <= result.topics.provenance.confidence <= 1.0
    assert len(result.topics.provenance.source_messages) > 0

    # Facts Provenance
    for fact in result.facts:
        assert fact.provenance.pipeline_stage == "FactExtractionStage"
        assert fact.provenance.artifact_id is not None
        assert 0.0 <= fact.provenance.confidence <= 1.0
        assert len(fact.provenance.source_messages) > 0
        assert fact.canonical_value.data_type != ""

    # Segments Provenance
    for seg in result.segments:
        assert seg.provenance.pipeline_stage == "SegmentStage"
        assert seg.start_message_id != ""
        assert seg.end_message_id != ""

    # Summaries Provenance
    for summary in result.summaries.values():
        assert summary.provenance.pipeline_stage == "SummaryStage"
        assert summary.template_name != ""


# ── 6. CQRS Repositories Separation ───────────────────────────────────────────

def test_cqrs_repositories_isolation(sample_conversation_messages):
    """Verify Read and Write repositories maintain strict CQRS separation."""
    storage = InMemoryConversationAnalysisStorage()
    read_repo = InMemoryConversationAnalysisReadRepository(storage)
    write_repo = InMemoryConversationAnalysisWriteRepository(storage)

    engine = ConversationAnalysisEngine(
        read_repo=read_repo,
        write_repo=write_repo,
    )

    result = engine.analyze_conversation(
        conversation_id="conv_cqrs_001",
        workspace_id=uuid.uuid4(),
        raw_messages=sample_conversation_messages,
    )

    # Read queries
    fetched = read_repo.get_by_conversation_id("conv_cqrs_001")
    assert fetched is not None
    assert fetched.analysis_id == result.analysis_id

    topics = read_repo.get_topics("conv_cqrs_001")
    assert topics is not None

    facts = read_repo.get_facts("conv_cqrs_001", category=FactCategory.BUDGET_REFERENCE)
    assert len(facts) >= 1

    summaries = read_repo.get_summaries("conv_cqrs_001")
    assert "EXECUTIVE" in summaries

    # Deletion via Write repository
    assert write_repo.delete_by_conversation_id("conv_cqrs_001") is True
    assert read_repo.get_by_conversation_id("conv_cqrs_001") is None


# ── 7. Strict Architectural Boundary Validation ───────────────────────────────

def test_strict_architectural_boundary_guard():
    """Verify AnalysisValidationFramework rejects illegal mutating or predictive fields."""
    framework = AnalysisValidationFramework()
    context = ConversationAnalysisContext(conversation_id="conv_test_boundary")

    # Inject forbidden recommendation / intent field
    context.set_artifact("predicted_intent", "BUY_NOW")
    context.set_artifact("recommendation_actions", ["SEND_DISCOUNT_COUPON"])

    validated = framework.validate(context)
    assert validated.diagnostics.is_valid is False
    assert any("Illegal field" in err for err in validated.diagnostics.validation_errors)


# ── 8. REST API Endpoints v1 Integration ──────────────────────────────────────

def test_rest_api_endpoints_v1(sample_conversation_messages):
    """Test all REST API endpoints under /api/v1/conversations/analysis/*."""
    client = TestClient(app)

    # 1. POST /api/v1/conversations/analysis/analyze
    conv_id = f"rest_conv_{uuid.uuid4().hex[:8]}"
    payload = {
        "conversation_id": conv_id,
        "messages": sample_conversation_messages,
        "metadata": {"test_source": "rest_client"},
    }

    response = client.post("/api/v1/conversations/analysis/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conv_id
    assert "metadata" in data
    assert "topics" in data
    assert "facts" in data
    assert "summaries" in data
    assert "segments" in data
    assert data["diagnostics"]["is_valid"] is True

    # 2. GET /api/v1/conversations/analysis/{conversation_id}
    res_get = client.get(f"/api/v1/conversations/analysis/{conv_id}")
    assert res_get.status_code == 200
    assert res_get.json()["conversation_id"] == conv_id

    # 3. GET /api/v1/conversations/analysis/{conversation_id}/summary
    res_sum = client.get(f"/api/v1/conversations/analysis/{conv_id}/summary?summary_type=EXECUTIVE")
    assert res_sum.status_code == 200
    assert res_sum.json()["summary_type"] == "EXECUTIVE"

    # 4. GET /api/v1/conversations/analysis/{conversation_id}/topics
    res_top = client.get(f"/api/v1/conversations/analysis/{conv_id}/topics")
    assert res_top.status_code == 200
    assert "primary_topic" in res_top.json()

    # 5. GET /api/v1/conversations/analysis/{conversation_id}/facts
    res_facts = client.get(f"/api/v1/conversations/analysis/{conv_id}/facts?category=BUDGET_REFERENCE")
    assert res_facts.status_code == 200
    facts_list = res_facts.json()
    assert len(facts_list) >= 1
    assert facts_list[0]["canonical_value"]["unit"] == "INR"

    # 6. GET /api/v1/conversations/analysis/{conversation_id}/segments
    res_seg = client.get(f"/api/v1/conversations/analysis/{conv_id}/segments")
    assert res_seg.status_code == 200
    assert len(res_seg.json()) >= 1

    # 7. GET /api/v1/conversations/analysis/{conversation_id}/metadata
    res_meta = client.get(f"/api/v1/conversations/analysis/{conv_id}/metadata")
    assert res_meta.status_code == 200
    assert res_meta.json()["message_count"] == 6

    # 8. GET /api/v1/conversations/analysis/system/taxonomies
    res_tax = client.get("/api/v1/conversations/analysis/system/taxonomies")
    assert res_tax.status_code == 200
    assert len(res_tax.json()) > 5

    # 9. GET /api/v1/conversations/analysis/system/templates
    res_tpl = client.get("/api/v1/conversations/analysis/system/templates")
    assert res_tpl.status_code == 200
    assert len(res_tpl.json()) >= 4
