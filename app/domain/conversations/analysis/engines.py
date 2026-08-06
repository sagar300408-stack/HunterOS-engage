"""
HunterOS Engage — Orchestration Engines & Metadata Extractor (Phase 2.2.1)

Coordinates extractors, templates, and telemetry to generate structured
analytical models for conversation topics, facts, summaries, and metadata.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.domain.conversations.analysis.extractors.base import (
    AbstractFactExtractor,
    AbstractSummaryGenerator,
    AbstractTopicExtractor,
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
    ConversationMetadata,
    ConversationSummary,
    ExtractedFact,
    FactCategory,
    NormalizedMessage,
    SummaryType,
    TopicAnalysis,
)
from app.domain.conversations.analysis.registry import (
    SummaryTemplateRegistry,
    default_summary_template_registry,
)
from app.domain.conversations.analysis.taxonomy import (
    TopicTaxonomy,
    default_topic_taxonomy,
)


class TopicDetectionEngine:
    """
    Orchestrates topic extractors and taxonomy matching.
    """

    def __init__(
        self,
        extractor: Optional[AbstractTopicExtractor] = None,
        taxonomy: Optional[TopicTaxonomy] = None,
    ) -> None:
        self._extractor = extractor or TaxonomyTopicExtractor(taxonomy=taxonomy or default_topic_taxonomy)

    def detect_topics(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> TopicAnalysis:
        return self._extractor.extract_topics(messages, context=context)


class KeyFactExtractionEngine:
    """
    Orchestrates specialized fact extractors across all key fact categories.
    """

    def __init__(self, extractors: Optional[List[AbstractFactExtractor]] = None) -> None:
        if extractors is not None:
            self._extractors = extractors
        else:
            self._extractors = [
                ContactInfoExtractor(),
                BudgetExtractor(),
                PropertyExtractor(),
                LocationExtractor(),
                DateExtractor(),
                CompanyInfoExtractor(),
                CustomerInfoExtractor(),
                ProductExtractor(),
                DocumentMentionExtractor(),
            ]

    def register_extractor(self, extractor: AbstractFactExtractor) -> None:
        """Add a custom fact extractor."""
        self._extractors.append(extractor)

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        all_facts: List[ExtractedFact] = []
        for extractor in self._extractors:
            try:
                facts = extractor.extract_facts(messages, context=context)
                all_facts.extend(facts)
            except Exception:
                continue
        return all_facts


class ConversationSummaryEngine:
    """
    Orchestrates multi-perspective summary generation using summary templates.
    """

    def __init__(
        self,
        generator: Optional[AbstractSummaryGenerator] = None,
        registry: Optional[SummaryTemplateRegistry] = None,
    ) -> None:
        self._registry = registry or default_summary_template_registry
        self._generator = generator or TemplateBasedSummaryGenerator(registry=self._registry)

    def generate_summaries(self, context: Any) -> Dict[str, ConversationSummary]:
        """Generate standard perspectives (Executive, Customer, Internal, Technical)."""
        summaries: Dict[str, ConversationSummary] = {}
        standard_types = [
            SummaryType.EXECUTIVE,
            SummaryType.CUSTOMER,
            SummaryType.INTERNAL,
            SummaryType.TECHNICAL,
        ]

        for stype in standard_types:
            summary = self._generator.generate_summary(stype, context)
            summaries[stype.value] = summary

        return summaries

    def generate_custom_summary(
        self,
        template_name: str,
        context: Any,
    ) -> ConversationSummary:
        """Generate summary using a specific custom template."""
        return self._generator.generate_summary(
            SummaryType.CUSTOM,
            context,
            template_name=template_name,
        )


class ConversationMetadataExtractor:
    """
    Extracts structural conversation telemetry, participant metadata,
    duration, and message distributions.
    """

    def extract_metadata(
        self,
        conversation_id: str,
        messages: List[NormalizedMessage],
        workspace_id: Optional[uuid.UUID] = None,
        raw_metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationMetadata:
        if not messages:
            return ConversationMetadata(
                conversation_id=conversation_id,
                workspace_id=workspace_id,
                message_count=0,
            )

        # Sort messages by timestamp to ensure chronological calculation
        sorted_msgs = sorted(messages, key=lambda m: m.timestamp)
        first_msg = sorted_msgs[0]
        last_msg = sorted_msgs[-1]

        duration_sec = max(0.0, (last_msg.timestamp - first_msg.timestamp).total_seconds())

        incoming_count = sum(1 for m in messages if m.direction.value == "INCOMING")
        outgoing_count = sum(1 for m in messages if m.direction.value == "OUTGOING")

        participants: Set[str] = {m.sender for m in messages if m.sender}
        channels: Set[str] = {m.channel for m in messages if m.channel}
        
        all_attachments: List[Dict[str, Any]] = []
        for m in messages:
            if m.attachments:
                all_attachments.extend(m.attachments)

        # Basic language detection heuristic (default English)
        languages = ["en"]

        message_types: Set[str] = {"text"}
        if all_attachments:
            message_types.add("media")

        return ConversationMetadata(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            duration_seconds=round(duration_sec, 2),
            message_count=len(messages),
            incoming_count=incoming_count,
            outgoing_count=outgoing_count,
            participants=sorted(list(participants)),
            communication_channels=sorted(list(channels)),
            languages=languages,
            attachments=all_attachments,
            message_types=sorted(list(message_types)),
            first_message_at=first_msg.timestamp,
            last_message_at=last_msg.timestamp,
        )
