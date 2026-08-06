"""
HunterOS Engage — Abstract Extractor Interfaces (Phase 2.2.1)

Defines the extractor contracts decoupled from high-level orchestration engines.
Extractors perform the low-level processing, pattern recognition, and extraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.models import (
    ConversationSummary,
    ExtractedFact,
    FactCategory,
    NormalizedMessage,
    SummaryType,
    TopicAnalysis,
)


class AbstractTopicExtractor(ABC):
    """Contract for extracting topics from conversation messages."""

    @abstractmethod
    def extract_topics(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> TopicAnalysis:
        """Extract primary, secondary, distributions, and timeline for topics."""
        pass


class AbstractFactExtractor(ABC):
    """Contract for extracting specific categories of key facts."""

    @property
    @abstractmethod
    def target_category(self) -> FactCategory:
        """The fact category handled by this extractor."""
        pass

    @abstractmethod
    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        """Extract facts belonging to target category with source references."""
        pass


class AbstractSummaryGenerator(ABC):
    """Contract for generating multi-perspective summaries."""

    @abstractmethod
    def generate_summary(
        self,
        summary_type: SummaryType,
        context: Any,
        template_name: Optional[str] = None,
    ) -> ConversationSummary:
        """Generate structured conversation summary for a given type or template."""
        pass
