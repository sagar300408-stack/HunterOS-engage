"""
HunterOS Engage V1 - Conversation Timeline Engine Test Suite
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Validates timeline construction, event extractors, milestone rules, important moments,
multi-view projections, lineage provenance, and strict architectural invariants.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import pytest

from app.domain.conversations.analysis.engine import ConversationAnalysisEngine
from app.domain.conversations.analysis.models import (
    AnalysisDiagnostics,
    ArtifactProvenance,
    CanonicalValue,
    ConversationAnalysisResult,
    ConversationMetadata,
    ConversationSegment,
    ExtractedFact,
    ExtractionMethod,
    FactCategory,
    MessageDirection,
    NormalizedMessage,
    SegmentType,
    SourceMessageRef,
    TopicAnalysis,
    TopicTimelineItem,
)
from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.engine import (
    ConversationTimelineEngine,
    default_conversation_timeline_engine,
)
from app.domain.conversations.timeline.extractors.base import AbstractTimelineEventExtractor
from app.domain.conversations.timeline.extractors.registry import TimelineEventExtractorRegistry
from app.domain.conversations.timeline.extractors.standard import (
    AgreementEventExtractor,
    BudgetEventExtractor,
    CustomerIntroEventExtractor,
    CustomTimelineEventExtractor,
    DateEventExtractor,
    DocumentEventExtractor,
    FollowUpEventExtractor,
    InformationSharedEventExtractor,
    LifecycleEventExtractor,
    MeetingEventExtractor,
    ObjectionEventExtractor,
    QuestionEventExtractor,
    RequirementEventExtractor,
)
from app.domain.conversations.timeline.milestones.base import AbstractMilestoneRule
from app.domain.conversations.timeline.milestones.registry import MilestoneRuleRegistry
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
    TimelinePipelineState,
    TimelineProvenance,
    TimelineScopeType,
    TimelineViewFormat,
)
from app.domain.conversations.timeline.moments.base import AbstractImportantMomentRule
from app.domain.conversations.timeline.moments.registry import ImportantMomentRegistry
from app.domain.conversations.timeline.normalizer import TimelineEventNormalizer
from app.domain.conversations.timeline.validation import (
    TimelineValidationError,
    TimelineValidationFramework,
)
from app.domain.conversations.timeline.views.registry import TimelineViewRegistry


@pytest.fixture
def sample_analysis_result() -> ConversationAnalysisResult:
    """Fixture providing rich mock analysis output for testing timeline engine."""
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    ws_id = uuid.uuid4()
    t0 = datetime(2026, 8, 6, 10, 0, 0, tzinfo=timezone.utc)

    facts = [
        ExtractedFact(
            fact_id=uuid.uuid4(),
            category=FactCategory.CUSTOMER_INFO,
            key="customer_name",
            raw_value="Rahul Verma",
            canonical_value=CanonicalValue(raw_value="Rahul Verma", normalized_value="Rahul Verma", data_type="string"),
            provenance=ArtifactProvenance(
                pipeline_stage="FACT_EXTRACTION",
                confidence=0.98,
                source_messages=[SourceMessageRef(message_id="msg-1", timestamp=t0)],
            ),
        ),
        ExtractedFact(
            fact_id=uuid.uuid4(),
            category=FactCategory.PROPERTY_REFERENCE,
            key="unit_type",
            raw_value="3BHK villa",
            canonical_value=CanonicalValue(raw_value="3BHK villa", normalized_value="3 BHK", data_type="string"),
            provenance=ArtifactProvenance(
                pipeline_stage="FACT_EXTRACTION",
                confidence=0.95,
                source_messages=[SourceMessageRef(message_id="msg-1", timestamp=t0)],
            ),
        ),
        ExtractedFact(
            fact_id=uuid.uuid4(),
            category=FactCategory.LOCATION_REFERENCE,
            key="location_preference",
            raw_value="Whitefield",
            canonical_value=CanonicalValue(raw_value="Whitefield", normalized_value="Whitefield, Bangalore", data_type="string"),
            provenance=ArtifactProvenance(
                pipeline_stage="FACT_EXTRACTION",
                confidence=0.95,
                source_messages=[SourceMessageRef(message_id="msg-1", timestamp=t0)],
            ),
        ),
        ExtractedFact(
            fact_id=uuid.uuid4(),
            category=FactCategory.BUDGET_REFERENCE,
            key="budget_max",
            raw_value="₹2.5 Crore",
            canonical_value=CanonicalValue(raw_value="₹2.5 Crore", normalized_value=25000000.0, data_type="currency", unit="INR"),
            provenance=ArtifactProvenance(
                pipeline_stage="FACT_EXTRACTION",
                confidence=0.99,
                source_messages=[SourceMessageRef(message_id="msg-3", timestamp=t0 + timedelta(seconds=45))],
            ),
        ),
        ExtractedFact(
            fact_id=uuid.uuid4(),
            category=FactCategory.DOCUMENT_MENTIONED,
            key="requested_collateral",
            raw_value="Brochure and floor plans",
            canonical_value=CanonicalValue(raw_value="Brochure and floor plans", normalized_value="Brochure", data_type="string"),
            provenance=ArtifactProvenance(
                pipeline_stage="FACT_EXTRACTION",
                confidence=0.92,
                source_messages=[SourceMessageRef(message_id="msg-3", timestamp=t0 + timedelta(seconds=45))],
            ),
        ),
    ]

    segments = [
        ConversationSegment(
            segment_type=SegmentType.GREETING,
            start_message_id="msg-1",
            end_message_id="msg-2",
            message_count=2,
            summary_snippet="Initial greeting and inquiry",
            provenance=ArtifactProvenance(pipeline_stage="SEGMENTATION", confidence=1.0),
        ),
        ConversationSegment(
            segment_type=SegmentType.DISCOVERY,
            start_message_id="msg-3",
            end_message_id="msg-4",
            message_count=2,
            summary_snippet="Requirement specification and budget discussion",
            provenance=ArtifactProvenance(pipeline_stage="SEGMENTATION", confidence=1.0),
        ),
        ConversationSegment(
            segment_type=SegmentType.CLOSING,
            start_message_id="msg-5",
            end_message_id="msg-5",
            message_count=1,
            summary_snippet="Site visit confirmation and agreement",
            provenance=ArtifactProvenance(pipeline_stage="SEGMENTATION", confidence=1.0),
        ),
    ]

    topics = TopicAnalysis(
        primary_topic="Luxury Villa Purchase",
        primary_taxonomy_path="real_estate/residential/luxury_villa",
        timeline=[
            TopicTimelineItem(
                topic_name="Site Visit Booking",
                taxonomy_path="real_estate/scheduling",
                message_id="msg-4",
                timestamp=t0 + timedelta(seconds=75),
                position_fraction=0.8,
            )
        ],
        provenance=ArtifactProvenance(pipeline_stage="TOPIC_DETECTION", confidence=0.95),
    )

    metadata = ConversationMetadata(
        conversation_id=conv_id,
        workspace_id=ws_id,
        duration_seconds=110.0,
        message_count=5,
        incoming_count=3,
        outgoing_count=2,
        participants=["customer", "agent"],
        first_message_at=t0,
        last_message_at=t0 + timedelta(seconds=110),
    )

    diagnostics = AnalysisDiagnostics(
        pipeline_execution_time_ms=25.0,
        is_valid=True,
    )

    return ConversationAnalysisResult(
        analysis_id=uuid.uuid4(),
        conversation_id=conv_id,
        workspace_id=ws_id,
        metadata=metadata,
        facts=facts,
        topics=topics,
        segments=segments,
        diagnostics=diagnostics,
    )


class TestConversationTimelineEngine:
    """Core test suite for Timeline Engine and pipeline stages."""

    def test_full_pipeline_execution(self, sample_analysis_result: ConversationAnalysisResult):
        """Tests end-to-end execution of the 8-stage timeline pipeline."""
        engine = ConversationTimelineEngine()
        timeline = engine.build_timeline(sample_analysis_result, customer_id="cust-101")

        assert timeline is not None
        assert isinstance(timeline, ConversationTimeline)
        assert timeline.conversation_id == sample_analysis_result.conversation_id
        assert timeline.workspace_id == sample_analysis_result.workspace_id
        assert timeline.customer_id == "cust-101"
        assert timeline.scope_type == TimelineScopeType.CONVERSATION

        # Check event stream
        stream = timeline.event_stream
        assert stream is not None
        assert isinstance(stream, ConversationEventStream)
        assert len(stream.events) >= 5

        # Check chronological ordering
        for i in range(len(stream.events) - 1):
            assert stream.events[i].occurred_at <= stream.events[i + 1].occurred_at
            assert stream.events[i].sequence_index == i
            assert stream.events[i].time_offset_seconds <= stream.events[i + 1].time_offset_seconds

        # Check milestones
        assert len(timeline.milestones) >= 3
        milestone_types = {m.milestone_type for m in timeline.milestones}
        assert MilestoneType.INITIAL_ENGAGEMENT in milestone_types
        assert MilestoneType.NEEDS_ALIGNED in milestone_types
        assert MilestoneType.BUDGET_ESTABLISHED in milestone_types

        # Check important moments
        assert len(timeline.important_moments) >= 2
        moment_types = {m.moment_type for m in timeline.important_moments}
        assert ImportantMomentType.FIRST_REQUIREMENT in moment_types
        assert ImportantMomentType.BUDGET_DISCUSSION in moment_types

        # Check diagnostics & validation
        assert timeline.diagnostics.is_valid is True
        assert len(timeline.diagnostics.validation_errors) == 0
        assert len(timeline.diagnostics.stages_executed) == 8
        assert timeline.metadata.duration_seconds == 110.0

    def test_custom_event_extractor_registration(self, sample_analysis_result: ConversationAnalysisResult):
        """Tests registering and executing a custom timeline event extractor."""
        class VIPPromotionEventExtractor(AbstractTimelineEventExtractor):
            @property
            def extractor_name(self) -> str:
                return "VIPPromotionEventExtractor"

            def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
                return [
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=context.conversation_id,
                        workspace_id=context.workspace_id,
                        event_type=TimelineEventType.CUSTOM_EVENT,
                        category=TimelineEventCategory.CUSTOM,
                        title="VIP Promotion Applied",
                        description="Special VIP tier discount applied.",
                        occurred_at=datetime(2026, 8, 6, 10, 1, 0, tzinfo=timezone.utc),
                        provenance=TimelineProvenance(
                            analysis_id=context.analysis_result.analysis_id if context.analysis_result else None,
                            pipeline_stage="EXTRACT_EVENTS",
                            extraction_method="VIP_RULE",
                        ),
                        confidence=1.0,
                        metadata={"vip_tier": "Gold"},
                    )
                ]

        custom_registry = TimelineEventExtractorRegistry(register_defaults=True)
        custom_registry.register(VIPPromotionEventExtractor())

        engine = ConversationTimelineEngine(extractor_registry=custom_registry)
        timeline = engine.build_timeline(sample_analysis_result)

        event_titles = [e.title for e in timeline.event_stream.events]
        assert "VIP Promotion Applied" in event_titles

    def test_custom_milestone_rule_registration(self, sample_analysis_result: ConversationAnalysisResult):
        """Tests registering a custom business milestone rule."""
        class HighValueLeadMilestoneRule(AbstractMilestoneRule):
            @property
            def rule_name(self) -> str:
                return "HighValueLeadMilestoneRule"

            @property
            def milestone_type(self) -> MilestoneType:
                return MilestoneType.CUSTOM_MILESTONE

            def evaluate(self, context: ConversationTimelineContext) -> Optional[TimelineMilestone]:
                for ev in context.normalized_events:
                    if ev.event_type == TimelineEventType.BUDGET_MENTIONED:
                        return TimelineMilestone(
                            milestone_id=uuid.uuid4(),
                            milestone_type=MilestoneType.CUSTOM_MILESTONE,
                            title="High Net Worth Opportunity",
                            description="Budget exceeds ₹2 Crore threshold.",
                            timestamp=ev.occurred_at,
                            source_event_ids=[ev.event_id],
                            confidence=1.0,
                            metadata={"tier": "HNW"},
                        )
                return None

        custom_rule_registry = MilestoneRuleRegistry(register_defaults=True)
        custom_rule_registry.register(HighValueLeadMilestoneRule())

        engine = ConversationTimelineEngine(milestone_registry=custom_rule_registry)
        timeline = engine.build_timeline(sample_analysis_result)

        milestone_titles = [m.title for m in timeline.milestones]
        assert "High Net Worth Opportunity" in milestone_titles

    def test_timeline_view_projections(self, sample_analysis_result: ConversationAnalysisResult):
        """Tests rendering multiple projection views from the timeline."""
        engine = ConversationTimelineEngine()
        timeline = engine.build_timeline(sample_analysis_result, customer_id="cust-101")

        # 1. Chronological Events View
        chrono_view = engine.render_view(timeline, "chronological_events")
        assert chrono_view["view"] == "chronological_events"
        assert chrono_view["total_events"] > 0
        assert "events" in chrono_view
        assert "provenance" in chrono_view["events"][0]

        # 2. Milestones Only View
        milestone_view = engine.render_view(timeline, "milestones_only")
        assert milestone_view["view"] == "milestones_only"
        assert milestone_view["total_milestones"] > 0
        assert "milestones" in milestone_view

        # 3. Important Moments View
        moments_view = engine.render_view(timeline, "important_moments")
        assert moments_view["view"] == "important_moments"
        assert moments_view["total_moments"] > 0
        assert "important_moments" in moments_view

        # 4. Executive Summary View
        exec_view = engine.render_view(timeline, "executive_summary")
        assert exec_view["view"] == "executive_summary"
        assert exec_view["duration_seconds"] == 110.0
        assert len(exec_view["key_milestones"]) > 0
        assert len(exec_view["key_moments"]) > 0

        # 5. Participant Specific View
        participant_view = engine.render_view(timeline, "participant_timeline", sender_type="customer")
        assert participant_view["view"] == "participant_timeline"
        assert participant_view["participant"] == "customer"

    def test_validation_framework_invariant_guards(self, sample_analysis_result: ConversationAnalysisResult):
        """Tests validation framework detecting invalid timestamps, sequence errors, and forbidden keys."""
        validator = TimelineValidationFramework()
        t0 = datetime(2026, 8, 6, 10, 0, 0, tzinfo=timezone.utc)

        # Context with forbidden keys (intent / sentiment)
        bad_context = ConversationTimelineContext(
            analysis_result=sample_analysis_result,
            conversation_id="conv-bad",
            workspace_id=uuid.uuid4(),
            normalized_events=[
                TimelineEvent(
                    event_id=uuid.uuid4(),
                    conversation_id="conv-bad",
                    workspace_id=uuid.uuid4(),
                    event_type=TimelineEventType.QUESTION_ASKED,
                    category=TimelineEventCategory.COMMUNICATION,
                    title="Inquiry",
                    description="Customer asked question",
                    occurred_at=t0,
                    sequence_index=0,
                    time_offset_seconds=0.0,
                    confidence=0.9,
                    metadata={"intent": "buy_house", "sentiment_score": 0.85},  # FORBIDDEN!
                )
            ]
        )

        errors = validator.validate(bad_context, raise_on_error=False)
        assert len(errors) >= 2
        assert any("forbidden key 'intent'" in err for err in errors)
        assert any("forbidden key 'sentiment_score'" in err for err in errors)

    def test_end_to_end_analysis_to_timeline_integration(self):
        """Tests full integration flow: Raw conversation -> ConversationAnalysisEngine -> ConversationTimelineEngine."""
        # 1. Run 2.2.1 Analysis Engine
        analysis_engine = ConversationAnalysisEngine()
        raw_messages = [
            {
                "id": "m1",
                "sender": "customer",
                "direction": "INCOMING",
                "content": "Hello, I am Priya Sharma. Looking for a 2BHK flat in Indiranagar under ₹1.2 Crore.",
                "timestamp": "2026-08-06T11:00:00Z",
            },
            {
                "id": "m2",
                "sender": "agent",
                "direction": "OUTGOING",
                "content": "Hello Priya! We have a 2BHK available. I can share the floor plan and schedule a site visit for Sunday.",
                "timestamp": "2026-08-06T11:02:00Z",
            },
            {
                "id": "m3",
                "sender": "customer",
                "direction": "INCOMING",
                "content": "Sunday 4 PM is great. Please send details. Agreed!",
                "timestamp": "2026-08-06T11:05:00Z",
            },
        ]
        raw_metadata = {"is_closed": True}

        analysis_result = analysis_engine.analyze_conversation(
            conversation_id="conv-int-001",
            raw_messages=raw_messages,
            raw_metadata=raw_metadata,
        )
        assert analysis_result is not None
        assert len(analysis_result.facts) >= 2

        # 2. Run 2.2.2 Timeline Engine
        timeline_engine = ConversationTimelineEngine()
        timeline = timeline_engine.build_timeline(analysis_result, customer_id="cust-priya")

        assert timeline is not None
        assert timeline.conversation_id == "conv-int-001"
        assert timeline.customer_id == "cust-priya"
        assert timeline.event_stream is not None
        assert len(timeline.event_stream.events) >= 4
        assert len(timeline.milestones) >= 2
        assert len(timeline.important_moments) >= 2
        assert timeline.diagnostics.is_valid is True

        # Check executive view output
        exec_summary = timeline_engine.render_view(timeline, "executive_summary")
        assert exec_summary["customer_id"] == "cust-priya"
        assert exec_summary["total_events"] >= 4
