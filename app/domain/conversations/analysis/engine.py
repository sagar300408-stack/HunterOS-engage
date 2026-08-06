"""
HunterOS Engage — Conversation Analysis Engine (Phase 2.2.1)

Unified public facade and orchestration engine for Conversation Analysis.
Provides the single public entry point for downstream intelligence modules and REST API.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.models import (
    ConversationAnalysisResult,
    ConversationMetadata,
    ConversationSegment,
    ConversationSummary,
    ExtractedFact,
    FactCategory,
    SummaryType,
    TopicAnalysis,
)
from app.domain.conversations.analysis.pipeline import ConversationPipelineRunner
from app.domain.conversations.analysis.registry import (
    AnalysisArtifactRegistry,
    SummaryTemplateRegistry,
    default_analysis_artifact_registry,
    default_summary_template_registry,
)
from app.domain.conversations.analysis.repository import (
    AbstractConversationAnalysisReadRepository,
    AbstractConversationAnalysisWriteRepository,
    InMemoryConversationAnalysisReadRepository,
    InMemoryConversationAnalysisStorage,
    InMemoryConversationAnalysisWriteRepository,
)
from app.domain.conversations.analysis.taxonomy import (
    TopicTaxonomy,
    default_topic_taxonomy,
)

logger = logging.getLogger("hunteros.conversations.analysis.engine")


class ConversationAnalysisEngine:
    """
    Conversation Analysis Engine (Phase 2.2.1).
    Transforms raw conversations into structured, deterministic business artifacts.
    """

    def __init__(
        self,
        pipeline_runner: Optional[ConversationPipelineRunner] = None,
        read_repo: Optional[AbstractConversationAnalysisReadRepository] = None,
        write_repo: Optional[AbstractConversationAnalysisWriteRepository] = None,
        artifact_registry: Optional[AnalysisArtifactRegistry] = None,
        template_registry: Optional[SummaryTemplateRegistry] = None,
        taxonomy: Optional[TopicTaxonomy] = None,
    ) -> None:
        self._pipeline_runner = pipeline_runner or ConversationPipelineRunner()

        if read_repo is None or write_repo is None:
            shared_storage = InMemoryConversationAnalysisStorage()
            self._read_repo = read_repo or InMemoryConversationAnalysisReadRepository(shared_storage)
            self._write_repo = write_repo or InMemoryConversationAnalysisWriteRepository(shared_storage)
        else:
            self._read_repo = read_repo
            self._write_repo = write_repo

        self._artifact_registry = artifact_registry or default_analysis_artifact_registry
        self._template_registry = template_registry or default_summary_template_registry
        self._taxonomy = taxonomy or default_topic_taxonomy

    @property
    def read_repository(self) -> AbstractConversationAnalysisReadRepository:
        return self._read_repo

    @property
    def write_repository(self) -> AbstractConversationAnalysisWriteRepository:
        return self._write_repo

    @property
    def artifact_registry(self) -> AnalysisArtifactRegistry:
        return self._artifact_registry

    @property
    def template_registry(self) -> SummaryTemplateRegistry:
        return self._template_registry

    @property
    def taxonomy(self) -> TopicTaxonomy:
        return self._taxonomy

    def analyze_conversation(
        self,
        conversation_id: str,
        workspace_id: Optional[uuid.UUID] = None,
        raw_messages: Optional[List[Any]] = None,
        raw_metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationAnalysisResult:
        """
        Execute the deterministic 9-stage analysis pipeline for a conversation
        and persist the resulting aggregate to the write repository.
        """
        context = ConversationAnalysisContext(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            raw_messages=raw_messages or [],
            raw_metadata=raw_metadata or {},
        )

        result = self._pipeline_runner.execute(context)
        self._write_repo.save(result)
        return result

    def analyze_messages(
        self,
        raw_messages: List[Any],
        workspace_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[str] = None,
    ) -> ConversationAnalysisResult:
        """
        Analyze an ephemeral stream or batch of messages.
        """
        conv_id = conversation_id or f"ephemeral_{uuid.uuid4().hex[:12]}"
        return self.analyze_conversation(
            conversation_id=conv_id,
            workspace_id=workspace_id,
            raw_messages=raw_messages,
        )

    # ── Public Query Facade ───────────────────────────────────────────────────

    def get_analysis(self, conversation_id: str) -> Optional[ConversationAnalysisResult]:
        """Fetch the full analysis aggregate for a conversation."""
        return self._read_repo.get_by_conversation_id(conversation_id)

    def get_summary(
        self,
        conversation_id: str,
        summary_type: Optional[SummaryType] = None,
    ) -> Optional[Union[ConversationSummary, Dict[str, ConversationSummary]]]:
        """Fetch summary projection, optionally for a specific perspective."""
        summaries = self._read_repo.get_summaries(conversation_id)
        if not summaries:
            return None
        if summary_type:
            return summaries.get(summary_type.value)
        return summaries

    def get_topics(self, conversation_id: str) -> Optional[TopicAnalysis]:
        """Fetch topic distribution and timeline for a conversation."""
        return self._read_repo.get_topics(conversation_id)

    def get_facts(
        self,
        conversation_id: str,
        category: Optional[FactCategory] = None,
    ) -> List[ExtractedFact]:
        """Fetch extracted facts, optionally filtered by category."""
        return self._read_repo.get_facts(conversation_id, category=category)

    def get_segments(self, conversation_id: str) -> List[ConversationSegment]:
        """Fetch conversation segments for a conversation."""
        return self._read_repo.get_segments(conversation_id)

    def get_metadata(self, conversation_id: str) -> Optional[ConversationMetadata]:
        """Fetch structural metadata for a conversation."""
        return self._read_repo.get_metadata(conversation_id)


# Global default engine instance for dependency injection
default_conversation_analysis_engine = ConversationAnalysisEngine()
