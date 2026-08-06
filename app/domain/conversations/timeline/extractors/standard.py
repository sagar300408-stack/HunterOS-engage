"""
HunterOS Engage V1 - Standard Timeline Event Extractors
Phase 2.2.2: Conversation Intelligence - Conversation Timeline

Deterministic extraction of business events from analyzed conversation artifacts.
Consumes only: Conversation Analysis Results, Metadata, Segments, Facts, Topics.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.models import (
    ConversationAnalysisResult,
    ExtractedFact,
    FactCategory,
)
from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.extractors.base import AbstractTimelineEventExtractor
from app.domain.conversations.timeline.models import (
    TimelineEvent,
    TimelineEventCategory,
    TimelineEventType,
    TimelineProvenance,
)


def _get_fact_timestamp(fact: ExtractedFact, fallback_dt: datetime) -> datetime:
    """Helper to extract best timestamp for a fact from its provenance."""
    if fact.provenance and fact.provenance.source_messages:
        for ref in fact.provenance.source_messages:
            if ref.timestamp:
                return ref.timestamp
    if fact.provenance and fact.provenance.generated_at:
        return fact.provenance.generated_at
    return fallback_dt


def _get_fact_msg_ids(fact: ExtractedFact) -> List[str]:
    """Helper to extract source message IDs from fact provenance."""
    if fact.provenance and fact.provenance.source_messages:
        return [ref.message_id for ref in fact.provenance.source_messages if ref.message_id]
    return []


def _get_fact_confidence(fact: ExtractedFact) -> float:
    """Helper to get confidence score from fact provenance."""
    if fact.provenance and hasattr(fact.provenance, "confidence"):
        return float(fact.provenance.confidence)
    return 1.0


class LifecycleEventExtractor(AbstractTimelineEventExtractor):
    """Extracts lifecycle start and completion events from conversation metadata & segments."""

    @property
    def extractor_name(self) -> str:
        return "LifecycleEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id

        first_dt = None
        last_dt = None
        participants = []

        if res.metadata:
            first_dt = res.metadata.first_message_at
            last_dt = res.metadata.last_message_at
            participants = res.metadata.participants

        first_dt = first_dt or res.analyzed_at or datetime.now(timezone.utc)
        last_dt = last_dt or first_dt

        first_msg_id = res.segments[0].start_message_id if res.segments else "msg_start"

        # Conversation Started Event
        prov_start = TimelineProvenance(
            analysis_id=analysis_id,
            source_message_ids=[first_msg_id] if first_msg_id else [],
            pipeline_stage="EXTRACT_EVENTS",
            extraction_method="LIFECYCLE_START",
            confidence=1.0,
        )
        events.append(
            TimelineEvent(
                event_id=uuid.uuid4(),
                conversation_id=conv_id,
                workspace_id=ws_id,
                event_type=TimelineEventType.CONVERSATION_STARTED,
                category=TimelineEventCategory.LIFECYCLE,
                title="Conversation Started",
                description=f"Conversation initiated with participants: {', '.join(participants) if participants else 'customer/agent'}.",
                occurred_at=first_dt,
                provenance=prov_start,
                confidence=1.0,
                metadata={"participants": participants},
            )
        )

        # Check for completed / closed conversation
        is_closed = False
        if res.metadata and getattr(res.metadata, "is_closed", False):
            is_closed = True
        elif res.segments and any(getattr(s.segment_type, "value", str(s.segment_type)) in ["CLOSING", "FOLLOW_UP"] for s in res.segments):
            is_closed = True

        if is_closed:
            last_msg_id = res.segments[-1].end_message_id if res.segments else "msg_end"
            prov_end = TimelineProvenance(
                analysis_id=analysis_id,
                source_message_ids=[last_msg_id] if last_msg_id else [],
                pipeline_stage="EXTRACT_EVENTS",
                extraction_method="LIFECYCLE_CLOSE",
                confidence=1.0,
            )
            events.append(
                TimelineEvent(
                    event_id=uuid.uuid4(),
                    conversation_id=conv_id,
                    workspace_id=ws_id,
                    event_type=TimelineEventType.CONVERSATION_CLOSED,
                    category=TimelineEventCategory.LIFECYCLE,
                    title="Conversation Closed",
                    description="Conversation completed and closed.",
                    occurred_at=last_dt,
                    provenance=prov_end,
                    confidence=1.0,
                    metadata={"duration_seconds": res.metadata.duration_seconds if res.metadata else 0.0},
                )
            )

        return events


class CustomerIntroEventExtractor(AbstractTimelineEventExtractor):
    """Extracts customer introduction and contact sharing events."""

    @property
    def extractor_name(self) -> str:
        return "CustomerIntroEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res or not res.facts:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        target_categories = {
            FactCategory.CUSTOMER_INFO.value,
            FactCategory.CONTACT_INFO.value,
            "CUSTOMER_INFO",
            "CONTACT_INFO",
            "NAME",
            "CONTACT",
        }

        for fact in res.facts:
            cat_val = fact.category.value if hasattr(fact.category, "value") else str(fact.category)
            if cat_val in target_categories:
                msg_ids = _get_fact_msg_ids(fact)
                occurred_at = _get_fact_timestamp(fact, fallback_dt)
                conf = _get_fact_confidence(fact)

                prov = TimelineProvenance(
                    analysis_id=analysis_id,
                    fact_id=fact.fact_id,
                    source_message_ids=msg_ids,
                    pipeline_stage="EXTRACT_EVENTS",
                    extraction_method="CUSTOMER_INTRO_FACT",
                    confidence=conf,
                )

                canonical_val = fact.canonical_value.normalized_value if (fact.canonical_value and hasattr(fact.canonical_value, "normalized_value")) else str(fact.raw_value)

                events.append(
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=conv_id,
                        workspace_id=ws_id,
                        event_type=TimelineEventType.CUSTOMER_INTRODUCED,
                        category=TimelineEventCategory.COMMUNICATION,
                        title="Customer Introduced",
                        description=f"{fact.key.replace('_', ' ').capitalize()}: {fact.raw_value}",
                        occurred_at=occurred_at,
                        provenance=prov,
                        confidence=conf,
                        metadata={
                            "fact_key": fact.key,
                            "fact_value": str(fact.raw_value),
                            "canonical_value": str(canonical_val),
                        },
                    )
                )

        return events


class RequirementEventExtractor(AbstractTimelineEventExtractor):
    """Extracts customer requirement and preference events."""

    @property
    def extractor_name(self) -> str:
        return "RequirementEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res or not res.facts:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        target_categories = {
            FactCategory.PROPERTY_REFERENCE.value,
            FactCategory.LOCATION_REFERENCE.value,
            "PROPERTY_REFERENCE",
            "LOCATION_REFERENCE",
            "PROPERTY",
            "LOCATION",
            "PREFERENCE",
            "REQUIREMENT",
        }

        for fact in res.facts:
            cat_val = fact.category.value if hasattr(fact.category, "value") else str(fact.category)
            if cat_val in target_categories:
                msg_ids = _get_fact_msg_ids(fact)
                occurred_at = _get_fact_timestamp(fact, fallback_dt)
                conf = _get_fact_confidence(fact)

                prov = TimelineProvenance(
                    analysis_id=analysis_id,
                    fact_id=fact.fact_id,
                    source_message_ids=msg_ids,
                    pipeline_stage="EXTRACT_EVENTS",
                    extraction_method="REQUIREMENT_FACT",
                    confidence=conf,
                )

                canonical_val = fact.canonical_value.normalized_value if (fact.canonical_value and hasattr(fact.canonical_value, "normalized_value")) else str(fact.raw_value)

                events.append(
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=conv_id,
                        workspace_id=ws_id,
                        event_type=TimelineEventType.REQUIREMENT_IDENTIFIED,
                        category=TimelineEventCategory.REQUIREMENT,
                        title="Requirement Identified",
                        description=f"Requirement for {fact.key.replace('_', ' ')}: {fact.raw_value}",
                        occurred_at=occurred_at,
                        provenance=prov,
                        confidence=conf,
                        metadata={
                            "requirement_type": fact.key,
                            "raw_value": str(fact.raw_value),
                            "canonical_value": str(canonical_val),
                        },
                    )
                )

        return events


class BudgetEventExtractor(AbstractTimelineEventExtractor):
    """Extracts budget mentions and commercial terms events."""

    @property
    def extractor_name(self) -> str:
        return "BudgetEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res or not res.facts:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        target_categories = {
            FactCategory.BUDGET_REFERENCE.value,
            "BUDGET_REFERENCE",
            "BUDGET",
            "FINANCIAL",
        }

        for fact in res.facts:
            cat_val = fact.category.value if hasattr(fact.category, "value") else str(fact.category)
            if cat_val in target_categories:
                msg_ids = _get_fact_msg_ids(fact)
                occurred_at = _get_fact_timestamp(fact, fallback_dt)
                conf = _get_fact_confidence(fact)

                prov = TimelineProvenance(
                    analysis_id=analysis_id,
                    fact_id=fact.fact_id,
                    source_message_ids=msg_ids,
                    pipeline_stage="EXTRACT_EVENTS",
                    extraction_method="BUDGET_FACT",
                    confidence=conf,
                )

                canonical_val = fact.canonical_value.normalized_value if (fact.canonical_value and hasattr(fact.canonical_value, "normalized_value")) else str(fact.raw_value)
                unit_val = getattr(fact.canonical_value, "unit", None) if fact.canonical_value else None

                events.append(
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=conv_id,
                        workspace_id=ws_id,
                        event_type=TimelineEventType.BUDGET_MENTIONED,
                        category=TimelineEventCategory.FINANCIAL,
                        title="Budget Mentioned",
                        description=f"Budget stated: {fact.raw_value}",
                        occurred_at=occurred_at,
                        provenance=prov,
                        confidence=conf,
                        metadata={
                            "raw_value": str(fact.raw_value),
                            "canonical_value": str(canonical_val),
                            "unit": unit_val,
                        },
                    )
                )

        return events


class DateEventExtractor(AbstractTimelineEventExtractor):
    """Extracts date mentions and timeframe events."""

    @property
    def extractor_name(self) -> str:
        return "DateEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res or not res.facts:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        target_categories = {
            FactCategory.DATE_REFERENCE.value,
            "DATE_REFERENCE",
            "DATE",
            "TIMELINE",
            "TIME",
        }

        for fact in res.facts:
            cat_val = fact.category.value if hasattr(fact.category, "value") else str(fact.category)
            if cat_val in target_categories:
                msg_ids = _get_fact_msg_ids(fact)
                occurred_at = _get_fact_timestamp(fact, fallback_dt)
                conf = _get_fact_confidence(fact)

                prov = TimelineProvenance(
                    analysis_id=analysis_id,
                    fact_id=fact.fact_id,
                    source_message_ids=msg_ids,
                    pipeline_stage="EXTRACT_EVENTS",
                    extraction_method="DATE_FACT",
                    confidence=conf,
                )

                canonical_val = fact.canonical_value.normalized_value if (fact.canonical_value and hasattr(fact.canonical_value, "normalized_value")) else str(fact.raw_value)

                events.append(
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=conv_id,
                        workspace_id=ws_id,
                        event_type=TimelineEventType.DATE_MENTIONED,
                        category=TimelineEventCategory.SCHEDULING,
                        title="Date Mentioned",
                        description=f"Date / Timeframe referenced: {fact.raw_value}",
                        occurred_at=occurred_at,
                        provenance=prov,
                        confidence=conf,
                        metadata={
                            "raw_value": str(fact.raw_value),
                            "canonical_value": str(canonical_val),
                        },
                    )
                )

        return events


class DocumentEventExtractor(AbstractTimelineEventExtractor):
    """Extracts document and brochure exchange events."""

    @property
    def extractor_name(self) -> str:
        return "DocumentEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res or not res.facts:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        target_categories = {
            FactCategory.DOCUMENT_MENTIONED.value,
            "DOCUMENT_MENTIONED",
            "DOCUMENT_MENTION",
            "DOCUMENT",
        }

        for fact in res.facts:
            cat_val = fact.category.value if hasattr(fact.category, "value") else str(fact.category)
            if cat_val in target_categories:
                msg_ids = _get_fact_msg_ids(fact)
                occurred_at = _get_fact_timestamp(fact, fallback_dt)
                conf = _get_fact_confidence(fact)

                prov = TimelineProvenance(
                    analysis_id=analysis_id,
                    fact_id=fact.fact_id,
                    source_message_ids=msg_ids,
                    pipeline_stage="EXTRACT_EVENTS",
                    extraction_method="DOCUMENT_FACT",
                    confidence=conf,
                )

                events.append(
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=conv_id,
                        workspace_id=ws_id,
                        event_type=TimelineEventType.DOCUMENT_SHARED,
                        category=TimelineEventCategory.DOCUMENT,
                        title="Document Shared",
                        description=f"Document referenced: {fact.raw_value}",
                        occurred_at=occurred_at,
                        provenance=prov,
                        confidence=conf,
                        metadata={
                            "document_name": str(fact.raw_value),
                        },
                    )
                )

        return events


class MeetingEventExtractor(AbstractTimelineEventExtractor):
    """Extracts meeting scheduling and site visit events from topic timelines and facts."""

    @property
    def extractor_name(self) -> str:
        return "MeetingEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        # 1. From Topic Timeline Items
        if res.topics and getattr(res.topics, "timeline", None):
            for item in res.topics.timeline:
                topic_lower = item.topic_name.lower()
                if any(k in topic_lower for k in ["site visit", "meeting", "appointment", "schedule", "visit"]):
                    prov = TimelineProvenance(
                        analysis_id=analysis_id,
                        source_message_ids=[item.message_id] if item.message_id else [],
                        pipeline_stage="EXTRACT_EVENTS",
                        extraction_method="MEETING_TOPIC_TIMELINE",
                        confidence=0.9,
                    )
                    events.append(
                        TimelineEvent(
                            event_id=uuid.uuid4(),
                            conversation_id=conv_id,
                            workspace_id=ws_id,
                            event_type=TimelineEventType.MEETING_SCHEDULED,
                            category=TimelineEventCategory.SCHEDULING,
                            title="Meeting / Site Visit Scheduled",
                            description=f"Meeting scheduled regarding {item.topic_name}.",
                            occurred_at=item.timestamp or fallback_dt,
                            provenance=prov,
                            confidence=0.9,
                            metadata={"topic_name": item.topic_name},
                        )
                    )

        # 2. From Facts with date/timeframe referencing visits
        for fact in (res.facts or []):
            val_str = str(fact.raw_value).lower()
            if any(k in val_str for k in ["visit", "meeting", "appointment", "demo", "sunday", "saturday", "tomorrow", "friday"]):
                msg_ids = _get_fact_msg_ids(fact)
                occurred_at = _get_fact_timestamp(fact, fallback_dt)
                prov = TimelineProvenance(
                    analysis_id=analysis_id,
                    fact_id=fact.fact_id,
                    source_message_ids=msg_ids,
                    pipeline_stage="EXTRACT_EVENTS",
                    extraction_method="MEETING_FACT",
                    confidence=0.9,
                )
                events.append(
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=conv_id,
                        workspace_id=ws_id,
                        event_type=TimelineEventType.MEETING_SCHEDULED,
                        category=TimelineEventCategory.SCHEDULING,
                        title="Meeting / Site Visit Scheduled",
                        description=f"Appointment / Visit planned: {fact.raw_value}",
                        occurred_at=occurred_at,
                        provenance=prov,
                        confidence=0.9,
                        metadata={"detail": str(fact.raw_value)},
                    )
                )

        return events


class QuestionEventExtractor(AbstractTimelineEventExtractor):
    """Extracts customer inquiries and discovery questions."""

    @property
    def extractor_name(self) -> str:
        return "QuestionEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        # Check facts or segments
        if res.segments:
            for seg in res.segments:
                seg_val = seg.segment_type.value if hasattr(seg.segment_type, "value") else str(seg.segment_type)
                if seg_val in ["DISCOVERY", "DISCUSSION"]:
                    prov = TimelineProvenance(
                        analysis_id=analysis_id,
                        source_message_ids=[seg.start_message_id] if seg.start_message_id else [],
                        pipeline_stage="EXTRACT_EVENTS",
                        extraction_method="DISCOVERY_SEGMENT",
                        confidence=0.9,
                    )
                    events.append(
                        TimelineEvent(
                            event_id=uuid.uuid4(),
                            conversation_id=conv_id,
                            workspace_id=ws_id,
                            event_type=TimelineEventType.QUESTION_ASKED,
                            category=TimelineEventCategory.COMMUNICATION,
                            title="Question Asked / Discovery Inquired",
                            description=seg.summary_snippet or "Customer and agent engaged in requirement discovery.",
                            occurred_at=fallback_dt,
                            provenance=prov,
                            confidence=0.9,
                            metadata={"segment_type": seg_val},
                        )
                    )

        return events


class InformationSharedEventExtractor(AbstractTimelineEventExtractor):
    """Extracts product and company details shared in the conversation."""

    @property
    def extractor_name(self) -> str:
        return "InformationSharedEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res or not res.facts:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        target_categories = {
            FactCategory.PRODUCT_REFERENCE.value,
            FactCategory.COMPANY_INFO.value,
            "PRODUCT_REFERENCE",
            "COMPANY_INFO",
            "PRODUCT",
            "AMENITY",
        }

        for fact in res.facts:
            cat_val = fact.category.value if hasattr(fact.category, "value") else str(fact.category)
            if cat_val in target_categories:
                msg_ids = _get_fact_msg_ids(fact)
                occurred_at = _get_fact_timestamp(fact, fallback_dt)
                conf = _get_fact_confidence(fact)

                prov = TimelineProvenance(
                    analysis_id=analysis_id,
                    fact_id=fact.fact_id,
                    source_message_ids=msg_ids,
                    pipeline_stage="EXTRACT_EVENTS",
                    extraction_method="INFO_SHARED_FACT",
                    confidence=conf,
                )

                events.append(
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=conv_id,
                        workspace_id=ws_id,
                        event_type=TimelineEventType.INFORMATION_SHARED,
                        category=TimelineEventCategory.COMMUNICATION,
                        title="Information Shared",
                        description=f"Information shared regarding {fact.key.replace('_', ' ')}: {fact.raw_value}",
                        occurred_at=occurred_at,
                        provenance=prov,
                        confidence=conf,
                        metadata={"fact_key": fact.key, "raw_value": str(fact.raw_value)},
                    )
                )

        return events


class ObjectionEventExtractor(AbstractTimelineEventExtractor):
    """Extracts customer objections, concerns, or blockers."""

    @property
    def extractor_name(self) -> str:
        return "ObjectionEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        # Check facts with objection or negotiation keys
        for fact in (res.facts or []):
            if "objection" in fact.key.lower() or "concern" in fact.key.lower() or "discount" in str(fact.raw_value).lower():
                msg_ids = _get_fact_msg_ids(fact)
                occurred_at = _get_fact_timestamp(fact, fallback_dt)
                conf = _get_fact_confidence(fact)

                prov = TimelineProvenance(
                    analysis_id=analysis_id,
                    fact_id=fact.fact_id,
                    source_message_ids=msg_ids,
                    pipeline_stage="EXTRACT_EVENTS",
                    extraction_method="OBJECTION_FACT",
                    confidence=conf,
                )
                events.append(
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=conv_id,
                        workspace_id=ws_id,
                        event_type=TimelineEventType.OBJECTION_RAISED,
                        category=TimelineEventCategory.OBJECTION,
                        title="Objection Raised",
                        description=f"Commercial / Preference Objection: {fact.raw_value}",
                        occurred_at=occurred_at,
                        provenance=prov,
                        confidence=conf,
                        metadata={"key": fact.key, "value": str(fact.raw_value)},
                    )
                )

        return events


class AgreementEventExtractor(AbstractTimelineEventExtractor):
    """Extracts agreements, commitments, and positive confirmations."""

    @property
    def extractor_name(self) -> str:
        return "AgreementEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.last_message_at if (res.metadata and res.metadata.last_message_at) else res.analyzed_at

        # Check closing segments or summaries
        if res.segments:
            for seg in res.segments:
                seg_val = seg.segment_type.value if hasattr(seg.segment_type, "value") else str(seg.segment_type)
                if seg_val in ["CLOSING", "NEGOTIATION"]:
                    prov = TimelineProvenance(
                        analysis_id=analysis_id,
                        source_message_ids=[seg.end_message_id] if seg.end_message_id else [],
                        pipeline_stage="EXTRACT_EVENTS",
                        extraction_method="AGREEMENT_SEGMENT",
                        confidence=0.90,
                    )
                    events.append(
                        TimelineEvent(
                            event_id=uuid.uuid4(),
                            conversation_id=conv_id,
                            workspace_id=ws_id,
                            event_type=TimelineEventType.AGREEMENT_REACHED,
                            category=TimelineEventCategory.COMMITMENT,
                            title="Agreement Reached",
                            description=seg.summary_snippet or "Mutual alignment or agreement reached on next steps.",
                            occurred_at=fallback_dt,
                            provenance=prov,
                            confidence=0.90,
                            metadata={"segment": seg_val},
                        )
                    )

        return events


class FollowUpEventExtractor(AbstractTimelineEventExtractor):
    """Extracts follow-up and callback requests."""

    @property
    def extractor_name(self) -> str:
        return "FollowUpEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.last_message_at if (res.metadata and res.metadata.last_message_at) else res.analyzed_at

        if res.segments:
            for seg in res.segments:
                seg_val = seg.segment_type.value if hasattr(seg.segment_type, "value") else str(seg.segment_type)
                if seg_val == "FOLLOW_UP":
                    prov = TimelineProvenance(
                        analysis_id=analysis_id,
                        source_message_ids=[seg.start_message_id] if seg.start_message_id else [],
                        pipeline_stage="EXTRACT_EVENTS",
                        extraction_method="FOLLOW_UP_SEGMENT",
                        confidence=0.88,
                    )
                    events.append(
                        TimelineEvent(
                            event_id=uuid.uuid4(),
                            conversation_id=conv_id,
                            workspace_id=ws_id,
                            event_type=TimelineEventType.FOLLOW_UP_REQUESTED,
                            category=TimelineEventCategory.COMMUNICATION,
                            title="Follow-up Requested",
                            description=seg.summary_snippet or "Follow-up action item planned.",
                            occurred_at=fallback_dt,
                            provenance=prov,
                            confidence=0.88,
                            metadata={"segment": seg_val},
                        )
                    )

        return events


class CustomTimelineEventExtractor(AbstractTimelineEventExtractor):
    """Pass-through extractor for custom facts and custom topic events."""

    @property
    def extractor_name(self) -> str:
        return "CustomTimelineEventExtractor"

    def extract(self, context: ConversationTimelineContext) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        res = context.analysis_result
        if not res or not res.facts:
            return events

        conv_id = context.conversation_id or res.conversation_id
        ws_id = context.workspace_id or res.workspace_id
        analysis_id = res.analysis_id
        fallback_dt = res.metadata.first_message_at if (res.metadata and res.metadata.first_message_at) else res.analyzed_at

        for fact in res.facts:
            cat_val = fact.category.value if hasattr(fact.category, "value") else str(fact.category)
            if cat_val in [FactCategory.CUSTOM.value, "CUSTOM", "OTHER"]:
                msg_ids = _get_fact_msg_ids(fact)
                occurred_at = _get_fact_timestamp(fact, fallback_dt)
                conf = _get_fact_confidence(fact)

                prov = TimelineProvenance(
                    analysis_id=analysis_id,
                    fact_id=fact.fact_id,
                    source_message_ids=msg_ids,
                    pipeline_stage="EXTRACT_EVENTS",
                    extraction_method="CUSTOM_FACT",
                    confidence=conf,
                )

                events.append(
                    TimelineEvent(
                        event_id=uuid.uuid4(),
                        conversation_id=conv_id,
                        workspace_id=ws_id,
                        event_type=TimelineEventType.CUSTOM_EVENT,
                        category=TimelineEventCategory.CUSTOM,
                        title=f"Custom Event: {fact.key}",
                        description=str(fact.raw_value),
                        occurred_at=occurred_at,
                        provenance=prov,
                        confidence=conf,
                        metadata={"custom_key": fact.key, "raw_value": str(fact.raw_value)},
                    )
                )

        return events
