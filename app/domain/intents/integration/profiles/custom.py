"""
HunterOS Engage V1 - Custom Composition Profile
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.intents.integration.models import (
    CompositionProfileType,
    CustomIntentContext,
    IntentIntelligenceContext,
)
from app.domain.intents.integration.profiles.base import CompositionProfile


class CustomProfile(CompositionProfile):
    """Composition profile applying caller-specified custom filters."""

    def __init__(self) -> None:
        super().__init__(
            profile_name="CustomProfile",
            profile_type=CompositionProfileType.CUSTOM,
            description="Custom caller-defined intent intelligence filtering and projection.",
        )

    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        filters = options or {}
        min_conf = float(filters.get("min_confidence", 0.0))
        allowed_cats = [c.upper() for c in filters.get("categories", [])]

        filtered_intents: List[Dict[str, Any]] = []
        if context.detection_result and context.detection_result.detected_intents:
            for det in context.detection_result.detected_intents:
                cat = det.category.value if hasattr(det.category, "value") else str(det.category)
                if det.confidence_score >= min_conf:
                    if not allowed_cats or cat.upper() in allowed_cats:
                        filtered_intents.append({
                            "intent_id": str(det.intent_id),
                            "intent_name": det.intent_type.value if hasattr(det.intent_type, "value") else str(det.intent_type),
                            "confidence": det.confidence_score,
                            "category": cat,
                        })

        filtered_conflicts: List[Dict[str, Any]] = []
        filtered_dependencies: List[Dict[str, Any]] = []
        if context.resolution_result and context.resolution_result.resolution_graph:
            for c in context.resolution_result.resolution_graph.conflicts:
                filtered_conflicts.append({
                    "conflict_id": str(c.conflict_id),
                    "description": c.description,
                    "severity": c.severity.value if hasattr(c.severity, "value") else str(c.severity),
                })
            for d in context.resolution_result.resolution_graph.dependencies:
                filtered_dependencies.append({
                    "dependency_id": str(d.dependency_id),
                    "is_blocking": d.is_blocking,
                    "reason": d.reason,
                })

        context.custom_view = CustomIntentContext(
            conversation_id=context.conversation_id,
            entity_id=context.entity_id,
            applied_filters=filters,
            filtered_intents=filtered_intents,
            filtered_conflicts=filtered_conflicts,
            filtered_dependencies=filtered_dependencies,
        )
