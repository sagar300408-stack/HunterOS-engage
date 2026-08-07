"""
HunterOS Engage V1 - Intent Integration Pipeline Context
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Execution context passed sequentially across the 7-stage Intent Integration Pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.integration.models import (
    CompositionProfileType,
    ContextCompletenessReport,
    ContextDiagnostics,
    ContextMetadata,
    ContextProvenance,
    IntentContextAnalytics,
    IntentContextGraph,
    IntentIntelligenceContext,
)
from app.domain.intents.integration.profiles.base import CompositionProfile
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult


@dataclass
class IntentIntegrationPipelineContext:
    """Shared execution context passing through the 7 integration stages."""
    conversation_id: str
    entity_id: str
    workspace_id: str
    profile_type: CompositionProfileType = CompositionProfileType.FULL
    custom_filters: Optional[Dict[str, Any]] = None
    options: Dict[str, Any] = field(default_factory=dict)

    # Ingested Artifacts
    detection_result: Optional[IntentDetectionResult] = None
    classification_result: Optional[IntentClassificationResult] = None
    evolution_result: Optional[IntentEvolutionResult] = None
    resolution_result: Optional[MultiIntentResolutionResult] = None
    conversation_analysis: Optional[Any] = None
    conversation_timeline: Optional[Any] = None
    conversation_insights: Optional[Any] = None

    # Pipeline Processing State
    active_profile: Optional[CompositionProfile] = None
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    context_graph: Optional[IntentContextGraph] = None
    completeness_report: Optional[ContextCompletenessReport] = None
    analytics: Optional[IntentContextAnalytics] = None
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    rules_applied: List[str] = field(default_factory=list)

    # Final Output
    assembled_context: Optional[IntentIntelligenceContext] = None
    is_valid: bool = True
