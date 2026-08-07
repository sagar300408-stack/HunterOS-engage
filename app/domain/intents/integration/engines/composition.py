"""
HunterOS Engage V1 - Intent Composition Engine
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Orchestrates profile-driven assembly of Intent Intelligence Contexts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.models import IntentEvolutionResult
from app.domain.intents.integration.assembler import IntentContextAssembler
from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext
from app.domain.intents.integration.registry import IntentContextRegistry, default_context_registry
from app.domain.intents.models import IntentDetectionResult
from app.domain.intents.resolution.models import MultiIntentResolutionResult

logger = logging.getLogger(__name__)


class IntentCompositionEngine:
    """
    Composition Engine coordinating profile selection and context assembly.
    """

    def __init__(
        self,
        assembler: Optional[IntentContextAssembler] = None,
        registry: Optional[IntentContextRegistry] = None,
    ) -> None:
        self.assembler = assembler or IntentContextAssembler()
        self.registry = registry or default_context_registry

    def compose(
        self,
        conversation_id: str,
        entity_id: str,
        workspace_id: str,
        profile_type: Union[str, CompositionProfileType] = CompositionProfileType.FULL,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        evolution_result: Optional[IntentEvolutionResult] = None,
        resolution_result: Optional[MultiIntentResolutionResult] = None,
        conversation_analysis: Optional[Any] = None,
        conversation_timeline: Optional[Any] = None,
        conversation_insights: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> IntentIntelligenceContext:
        profile = self.registry.get_profile(profile_type)

        context = self.assembler.assemble(
            conversation_id=conversation_id,
            entity_id=entity_id,
            workspace_id=workspace_id,
            detection_result=detection_result,
            classification_result=classification_result,
            evolution_result=evolution_result,
            resolution_result=resolution_result,
            conversation_analysis=conversation_analysis,
            conversation_timeline=conversation_timeline,
            conversation_insights=conversation_insights,
            profile=profile,
            options=options,
        )

        return context
