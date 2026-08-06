"""
HunterOS Engage V1 - Shared Test Helpers for Insight Engine
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from app.domain.conversations.analysis.models import (
    AnalysisDiagnostics,
    ArtifactProvenance,
    CanonicalValue,
    ConversationAnalysisResult,
    ConversationMetadata,
    ExtractedFact,
    ExtractionMethod,
    FactCategory,
    SourceMessageRef,
    TopicAnalysis,
    TopicDistribution,
)
from app.domain.conversations.timeline.models import (
    ConversationEventStream,
    ConversationTimeline,
    ImportantMoment,
    ImportantMomentType,
    TimelineDiagnostics,
    TimelineEvent,
    TimelineEventCategory,
    TimelineEventType,
    TimelineMetadata,
    TimelineMilestone,
    TimelineProvenance,
    TimelineScopeType,
)


def create_mock_extracted_fact(
    category: FactCategory,
    key: str,
    value: Any,
    confidence: float = 0.95,
    source_message_ids: Optional[List[str]] = None,
) -> ExtractedFact:
    msg_ids = source_message_ids or ["msg-1"]
    src_refs = [SourceMessageRef(message_id=mid) for mid in msg_ids]
    provenance = ArtifactProvenance(
        pipeline_stage="fact_extraction",
        confidence=confidence,
        source_messages=src_refs,
        extraction_method=ExtractionMethod.RULE_BASED,
    )
    canonical = CanonicalValue(
        raw_value=value,
        normalized_value=value,
        data_type="string",
    )
    return ExtractedFact(
        fact_id=uuid.uuid4(),
        category=category,
        key=key,
        raw_value=value,
        canonical_value=canonical,
        provenance=provenance,
    )


def create_mock_analysis_result(
    conversation_id: str = "conv-test-1",
    workspace_id: Optional[uuid.UUID] = None,
    customer_id: Optional[str] = "cust-test-1",
    facts: Optional[List[ExtractedFact]] = None,
    primary_topics: Optional[List[str]] = None,
) -> ConversationAnalysisResult:
    ws_id = workspace_id or uuid.uuid4()
    facts = facts or []
    topics_list = primary_topics or ["General Inquiry"]
    provenance = ArtifactProvenance(
        pipeline_stage="topic_analysis",
        confidence=0.95,
        source_messages=[SourceMessageRef(message_id="msg-1")],
        extraction_method=ExtractionMethod.RULE_BASED,
    )
    topic_analysis = TopicAnalysis(
        primary_topic=topics_list[0],
        primary_taxonomy_path=f"real_estate/{topics_list[0].lower().replace(' ', '_')}",
        secondary_topics=topics_list[1:],
        distribution=[
            TopicDistribution(
                topic_name=t,
                taxonomy_path=f"real_estate/{t.lower().replace(' ', '_')}",
                category="inquiry",
                frequency=1,
                weight=1.0 / max(len(topics_list), 1),
                provenance=provenance,
            )
            for t in topics_list
        ],
        timeline=[],
        provenance=provenance,
    )
    return ConversationAnalysisResult(
        analysis_id=uuid.uuid4(),
        conversation_id=conversation_id,
        workspace_id=ws_id,
        analyzed_at=datetime.now(timezone.utc),
        metadata=ConversationMetadata(
            conversation_id=conversation_id,
            workspace_id=ws_id,
            message_count=10,
            duration_seconds=120.0,
        ),
        topics=topic_analysis,
        facts=facts,
        diagnostics=AnalysisDiagnostics(
            pipeline_duration_ms=5.0,
            stages_executed=["stage1", "stage2"],
            stage_timings_ms={},
            warnings=[],
            errors=[],
        ),
    )


def create_mock_timeline(
    conversation_id: str = "conv-test-1",
    workspace_id: Optional[uuid.UUID] = None,
    customer_id: Optional[str] = "cust-test-1",
    events: Optional[List[TimelineEvent]] = None,
    milestones: Optional[List[TimelineMilestone]] = None,
    moments: Optional[List[ImportantMoment]] = None,
) -> ConversationTimeline:
    ws_id = workspace_id or uuid.uuid4()
    events = events or []
    milestones = milestones or []
    moments = moments or []
    tl_id = uuid.uuid4()
    stream_id = uuid.uuid4()

    stream = ConversationEventStream(
        stream_id=stream_id,
        conversation_id=conversation_id,
        workspace_id=ws_id,
        customer_id=customer_id,
        events=events,
    )

    metadata = TimelineMetadata(
        timeline_id=tl_id,
        conversation_id=conversation_id,
        workspace_id=ws_id,
        customer_id=customer_id,
        scope_type=TimelineScopeType.CONVERSATION,
        total_events=len(events),
        total_milestones=len(milestones),
        total_moments=len(moments),
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        duration_seconds=100.0,
        event_category_distribution={},
    )

    diagnostics = TimelineDiagnostics(
        pipeline_execution_time_ms=4.0,
        stage_timings_ms={},
        stages_executed=["all"],
        warnings=[],
        validation_errors=[],
        is_valid=True,
    )

    return ConversationTimeline(
        timeline_id=tl_id,
        conversation_id=conversation_id,
        workspace_id=ws_id,
        customer_id=customer_id,
        scope_type=TimelineScopeType.CONVERSATION,
        metadata=metadata,
        event_stream=stream,
        milestones=milestones,
        important_moments=moments,
        diagnostics=diagnostics,
    )


def create_mock_timeline_event(
    event_type: TimelineEventType,
    category: TimelineEventCategory,
    title: str,
    description: str,
    source_message_ids: Optional[List[str]] = None,
    occurred_at: Optional[datetime] = None,
) -> TimelineEvent:
    ev_id = uuid.uuid4()
    msg_ids = source_message_ids or ["msg-1"]
    provenance = TimelineProvenance(
        analysis_id=uuid.uuid4(),
        source_message_ids=msg_ids,
    )
    return TimelineEvent(
        event_id=ev_id,
        conversation_id="conv-test-1",
        workspace_id=uuid.uuid4(),
        event_type=event_type,
        category=category,
        title=title,
        description=description,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        provenance=provenance,
    )


def create_mock_important_moment(
    moment_type: ImportantMomentType,
    title: str,
    significance: str,
    source_message_id: Optional[str] = "msg-1",
    source_event_id: Optional[uuid.UUID] = None,
) -> ImportantMoment:
    return ImportantMoment(
        moment_id=uuid.uuid4(),
        moment_type=moment_type,
        title=title,
        significance=significance,
        timestamp=datetime.now(timezone.utc),
        source_message_id=source_message_id,
        source_event_id=source_event_id or uuid.uuid4(),
        snippet=significance,
    )
