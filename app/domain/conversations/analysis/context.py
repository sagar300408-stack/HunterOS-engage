"""
HunterOS Engage — Conversation Analysis Context (Phase 2.2.1)

Provides a unified mutable execution context passed across all independent
pipeline stages. Stages read and write only through this context.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.models import (
    AnalysisDiagnostics,
    ArtifactProvenance,
    ConversationAnalysisResult,
    ConversationMetadata,
    ConversationSegment,
    ConversationSummary,
    ExtractedFact,
    NormalizedMessage,
    PipelineState,
    TopicAnalysis,
)


@dataclass
class ConversationAnalysisContext:
    """
    Execution context that flows through the 8-step pipeline stages.
    Contains raw inputs, normalized data, extracted intelligence, telemetry,
    and arbitrary dynamic artifacts.
    """

    conversation_id: Optional[str] = None
    workspace_id: Optional[uuid.UUID] = None
    raw_messages: List[Any] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    # Stage outputs
    normalized_messages: List[NormalizedMessage] = field(default_factory=list)
    metadata: Optional[ConversationMetadata] = None
    segments: List[ConversationSegment] = field(default_factory=list)
    topics: Optional[TopicAnalysis] = None
    facts: List[ExtractedFact] = field(default_factory=list)
    summaries: Dict[str, ConversationSummary] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)

    # Execution telemetry
    diagnostics: AnalysisDiagnostics = field(default_factory=AnalysisDiagnostics)
    state: PipelineState = PipelineState.INITIALIZED
    start_time: float = field(default_factory=time.perf_counter)

    def add_stage_timing(self, stage_name: str, duration_ms: float) -> None:
        """Record execution time for an individual pipeline stage."""
        stage_timings = dict(self.diagnostics.stage_timings_ms)
        stage_timings[stage_name] = duration_ms
        stages_exec = list(self.diagnostics.stages_executed)
        if stage_name not in stages_exec:
            stages_exec.append(stage_name)
        
        self.diagnostics = AnalysisDiagnostics(
            pipeline_execution_time_ms=self.diagnostics.pipeline_execution_time_ms + duration_ms,
            stage_timings_ms=stage_timings,
            stages_executed=stages_exec,
            warnings=self.diagnostics.warnings,
            validation_errors=self.diagnostics.validation_errors,
            is_valid=self.diagnostics.is_valid,
        )

    def add_warning(self, warning_message: str) -> None:
        """Append non-fatal execution warning."""
        warnings = list(self.diagnostics.warnings)
        warnings.append(warning_message)
        self.diagnostics = AnalysisDiagnostics(
            pipeline_execution_time_ms=self.diagnostics.pipeline_execution_time_ms,
            stage_timings_ms=self.diagnostics.stage_timings_ms,
            stages_executed=self.diagnostics.stages_executed,
            warnings=warnings,
            validation_errors=self.diagnostics.validation_errors,
            is_valid=self.diagnostics.is_valid,
        )

    def add_error(self, error_message: str) -> None:
        """Append fatal or non-fatal validation error and flag validity."""
        errors = list(self.diagnostics.validation_errors)
        errors.append(error_message)
        self.diagnostics = AnalysisDiagnostics(
            pipeline_execution_time_ms=self.diagnostics.pipeline_execution_time_ms,
            stage_timings_ms=self.diagnostics.stage_timings_ms,
            stages_executed=self.diagnostics.stages_executed,
            warnings=self.diagnostics.warnings,
            validation_errors=errors,
            is_valid=False,
        )

    def set_artifact(self, key: str, value: Any) -> None:
        """Store dynamic artifact by key."""
        self.artifacts[key] = value

    def get_artifact(self, key: str, default: Any = None) -> Any:
        """Retrieve dynamic artifact by key."""
        return self.artifacts.get(key, default)

    def build_result(self) -> ConversationAnalysisResult:
        """
        Assemble the final immutable aggregate root from current context state.
        """
        total_time_ms = (time.perf_counter() - self.start_time) * 1000.0
        final_diag = AnalysisDiagnostics(
            pipeline_execution_time_ms=total_time_ms,
            stage_timings_ms=self.diagnostics.stage_timings_ms,
            stages_executed=self.diagnostics.stages_executed,
            warnings=self.diagnostics.warnings,
            validation_errors=self.diagnostics.validation_errors,
            is_valid=self.diagnostics.is_valid and len(self.diagnostics.validation_errors) == 0,
        )

        # Fallback metadata if not set
        meta = self.metadata or ConversationMetadata(
            conversation_id=self.conversation_id or "unknown",
            workspace_id=self.workspace_id,
            message_count=len(self.normalized_messages),
        )

        # Fallback topic analysis if empty
        topics = self.topics or TopicAnalysis(
            primary_topic="General Inquiry",
            primary_taxonomy_path="general/inquiry",
            provenance=ArtifactProvenance(
                pipeline_stage="TopicStage",
                confidence=1.0,
            ),
        )

        return ConversationAnalysisResult(
            conversation_id=self.conversation_id or meta.conversation_id,
            workspace_id=self.workspace_id,
            analyzed_at=datetime.now(timezone.utc),
            metadata=meta,
            segments=self.segments,
            topics=topics,
            facts=self.facts,
            summaries=self.summaries,
            custom_artifacts=self.artifacts,
            diagnostics=final_diag,
        )
