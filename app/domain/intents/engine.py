"""
HunterOS Engage V1 - Intent Detection Engine Facade
Public orchestrator and API entry point for the Intent Intelligence bounded context.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from app.domain.conversations.analysis.models import ConversationAnalysisResult
from app.domain.conversations.insight.models import ConversationInsightResult
from app.domain.conversations.timeline.models import ConversationTimeline
from app.domain.intents.context import IntentDetectionContext
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.pipeline import IntentPipelineRunner
from app.domain.intents.query import IntentQueryEngine, default_intent_query_engine
from app.domain.intents.recognizer import IntentRecognizer
from app.domain.intents.repository import (
    IntentRepository,
    default_intent_repository,
)
from app.domain.intents.resolver import IntentResolver
from app.domain.intents.validation import IntentValidator

logger = logging.getLogger(__name__)


class IntentDetectionEngine:
    """
    Public Facade for the Intent Detection Bounded Context.
    Identifies customer objectives strictly from Conversation Intelligence artifacts.
    """

    def __init__(
        self,
        runner: Optional[IntentPipelineRunner] = None,
        repository: Optional[IntentRepository] = None,
        query_engine: Optional[IntentQueryEngine] = None,
        recognizer: Optional[IntentRecognizer] = None,
        validator: Optional[IntentValidator] = None,
        resolver: Optional[IntentResolver] = None,
    ):
        self._repository = repository or default_intent_repository
        self._runner = runner or IntentPipelineRunner(
            recognizer=recognizer,
            validator=validator,
            resolver=resolver,
        )
        self._query_engine = query_engine or default_intent_query_engine

    @property
    def repository(self) -> IntentRepository:
        return self._repository

    @property
    def query_engine(self) -> IntentQueryEngine:
        return self._query_engine

    def detect_intents(
        self,
        analysis_result: Optional[ConversationAnalysisResult] = None,
        timeline: Optional[ConversationTimeline] = None,
        insight_result: Optional[ConversationInsightResult] = None,
        conversation_id: Optional[str] = None,
        workspace_id: Optional[uuid.UUID] = None,
        customer_id: Optional[str] = None,
    ) -> IntentDetectionResult:
        """
        Executes the 6-stage deterministic Intent Detection Pipeline.
        """
        cid = conversation_id or ""
        if not cid:
            if analysis_result:
                cid = str(analysis_result.conversation_id)
            elif timeline:
                cid = str(timeline.conversation_id)
            elif insight_result:
                cid = str(insight_result.conversation_id)

        ws_id = workspace_id
        if not ws_id:
            if analysis_result and analysis_result.workspace_id:
                ws_id = uuid.UUID(str(analysis_result.workspace_id))
            elif timeline and timeline.workspace_id:
                ws_id = uuid.UUID(str(timeline.workspace_id))
            elif insight_result and insight_result.workspace_id:
                ws_id = uuid.UUID(str(insight_result.workspace_id))

        c_id = customer_id
        if not c_id:
            for art in (analysis_result, timeline, insight_result):
                c = getattr(art, "customer_id", None)
                if c:
                    c_id = str(c)
                    break

        context = IntentDetectionContext(
            analysis_result=analysis_result,
            timeline=timeline,
            insight_result=insight_result,
            conversation_id=cid,
            workspace_id=ws_id,
            customer_id=c_id,
        )

        result = self._runner.execute(context)
        self._repository.save(result)
        logger.info(
            "Intent Detection Pipeline completed for conversation %s: %d intents detected.",
            cid,
            len(result.intents),
        )
        return result


# Default singleton instance
default_intent_detection_engine = IntentDetectionEngine()
