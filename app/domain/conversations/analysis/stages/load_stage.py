"""
HunterOS Engage — Load Stage (Phase 2.2.1)

Loads raw messages into the analysis context from repository, database, or direct payload.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.models import PipelineState
from app.domain.conversations.analysis.stages.base import PipelineStage


class LoadStage(PipelineStage):
    """Pipeline stage responsible for loading raw conversation messages."""

    def __init__(self, loader_func: Optional[Callable[[str], List[Any]]] = None) -> None:
        self._loader_func = loader_func

    @property
    def stage_name(self) -> str:
        return "LoadStage"

    @property
    def target_state(self) -> PipelineState:
        return PipelineState.LOADING

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        if not context.raw_messages and context.conversation_id and self._loader_func:
            loaded = self._loader_func(context.conversation_id)
            context.raw_messages = loaded or []

        if not context.raw_messages:
            context.add_warning("No raw messages loaded for conversation analysis.")

        return context
