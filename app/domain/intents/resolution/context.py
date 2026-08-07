"""
HunterOS Engage V1 - Multi-Intent Resolution Execution Context
Encapsulates runtime state, artifact payloads, and diagnostic tracing across resolution stages.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import (
    DominantIntent,
    IntentConflict,
    IntentDependency,
    IntentNode,
    IntentRelationship,
    IntentResolutionGraph,
    IntentResolutionGroup,
    MultiIntentResolutionResult,
)


class MultiIntentResolutionContext:
    """
    Execution context passed across the 9 stages of the resolution pipeline.
    Maintains inputs, normalized nodes, graph snapshot, resolved groups, and diagnostics.
    """

    def __init__(
        self,
        conversation_id: str,
        entity_id: str = "",
        entity_type: str = "CUSTOMER",
        workspace_id: Optional[uuid.UUID] = None,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        conversation_analysis: Optional[Any] = None,
        conversation_timeline: Optional[Any] = None,
        conversation_insight: Optional[Any] = None,
        rule_pack_names: Optional[List[str]] = None,
        plugin_names: Optional[List[str]] = None,
        custom_parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.conversation_id: str = conversation_id
        self.entity_id: str = entity_id or (detection_result.customer_id if detection_result and detection_result.customer_id else "unknown_entity")
        self.entity_type: str = entity_type
        self.workspace_id: Optional[uuid.UUID] = workspace_id or (detection_result.workspace_id if detection_result else None)

        # Artifact Inputs
        self.detection_result: Optional[IntentDetectionResult] = detection_result
        self.classification_result: Optional[IntentClassificationResult] = classification_result
        self.evolution_result: Optional[IntentEvolutionResult] = evolution_result
        self.conversation_analysis: Optional[Any] = conversation_analysis
        self.conversation_timeline: Optional[Any] = conversation_timeline
        self.conversation_insight: Optional[Any] = conversation_insight

        self.rule_pack_names: List[str] = rule_pack_names or []
        self.plugin_names: List[str] = plugin_names or []
        self.custom_parameters: Dict[str, Any] = custom_parameters or {}

        # Pipeline State
        self.raw_intent_items: List[Dict[str, Any]] = []
        self.normalized_nodes: Dict[str, IntentNode] = {}  # Keyed by str(intent_id)
        self.resolution_graph: Optional[IntentResolutionGraph] = None
        self.analyzed_relationships: List[IntentRelationship] = []
        self.analyzed_conflicts: List[IntentConflict] = []
        self.analyzed_dependencies: List[IntentDependency] = []
        self.resolved_groups: List[IntentResolutionGroup] = []
        self.dominant_intents: List[DominantIntent] = []

        # Diagnostics & Traceability
        self.start_time: float = time.perf_counter()
        self.stage_timings_ms: Dict[str, float] = {}
        self.stages_executed: List[str] = []
        self.rules_evaluated_count: int = 0
        self.strategies_evaluated_count: int = 0
        self.rule_packs_applied: List[str] = []
        self.plugins_applied: List[str] = []
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []

        # Output Aggregate Root
        self.result: Optional[MultiIntentResolutionResult] = None

    def record_stage_timing(self, stage_name: str, duration_ms: float) -> None:
        self.stage_timings_ms[stage_name] = duration_ms
        self.stages_executed.append(stage_name)

    def add_validation_error(self, message: str) -> None:
        self.validation_errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000.0
