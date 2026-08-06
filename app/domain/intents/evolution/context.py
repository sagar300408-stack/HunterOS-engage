"""
HunterOS Engage V1 - Intent Evolution Execution Context
Thread-safe isolated state container passed across the 8-stage evolution pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.domain.conversations.timeline.models import ConversationTimeline
from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import (
    EntityType,
    EvolutionDiagnostics,
    EvolutionMetadata,
    IntentEvolutionEvent,
    IntentEvolutionEventStream,
    IntentEvolutionResult,
    IntentHistory,
    IntentStateSnapshot,
    IntentTimeline,
)
from app.domain.intents.models import IntentDetectionResult


class IntentEvolutionContext:
    """
    Mutable isolated execution context for a single evolution pipeline run.
    """

    def __init__(
        self,
        entity_id: str,
        current_conversation_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        timeline: Optional[ConversationTimeline] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ):
        # ── Inputs ───────────────────────────────────────────────────────────
        self.entity_id: str = entity_id
        self.current_conversation_id: str = current_conversation_id
        self.entity_type: EntityType = entity_type
        self.workspace_id: Optional[uuid.UUID] = workspace_id
        self.detection_result: Optional[IntentDetectionResult] = detection_result
        self.classification_result: Optional[IntentClassificationResult] = classification_result
        self.conversation_timeline: Optional[ConversationTimeline] = timeline
        self.conversation_metadata: Dict[str, Any] = conversation_metadata or {}

        # ── Pipeline State ───────────────────────────────────────────────────
        self.historical_snapshots: List[IntentStateSnapshot] = []
        self.historical_stream: IntentEvolutionEventStream = IntentEvolutionEventStream(
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            workspace_id=self.workspace_id,
        )
        self.current_snapshots: List[IntentStateSnapshot] = []
        self.snapshot_diffs: List[Dict[str, Any]] = []
        self.new_events: List[IntentEvolutionEvent] = []
        self.updated_stream: IntentEvolutionEventStream = self.historical_stream
        self.projected_timelines: Dict[uuid.UUID, IntentTimeline] = {}
        self.histories: Dict[uuid.UUID, IntentHistory] = {}

        # ── Diagnostics & Telemetry ──────────────────────────────────────────
        self.stage_timings: Dict[str, float] = {}
        self.stages_executed: List[str] = []
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []
        self.strategies_evaluated_count: int = 0
        self.created_at: datetime = datetime.now(timezone.utc)
        self.result: Optional[IntentEvolutionResult] = None

    def record_stage_timing(self, stage_name: str, elapsed_ms: float) -> None:
        """Record execution latency for a pipeline stage."""
        self.stage_timings[stage_name] = round(elapsed_ms, 3)
        self.stages_executed.append(stage_name)

    def append_event(self, event: IntentEvolutionEvent) -> None:
        """Append a new evolution event to context and updated event stream."""
        self.new_events.append(event)
        self.updated_stream = self.updated_stream.append(event)

    def add_validation_error(self, message: str) -> None:
        """Record a critical invariant violation."""
        self.validation_errors.append(message)

    def add_warning(self, message: str) -> None:
        """Record a non-fatal telemetry warning."""
        self.warnings.append(message)
