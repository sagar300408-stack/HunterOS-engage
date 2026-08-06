"""
HunterOS Engage V1 - Intent Evolution Engine
Domain facade orchestrating context creation, pipeline execution, and repository persistence.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import uuid

from app.domain.conversations.timeline.models import ConversationTimeline
from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.evolution.context import IntentEvolutionContext
from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionResult,
)
from app.domain.intents.evolution.pipeline import IntentEvolutionPipeline
from app.domain.intents.evolution.repository import (
    IntentEvolutionRepository,
    default_evolution_repository,
)
from app.domain.intents.evolution.strategies.registry import (
    EvolutionStrategyRegistry,
    default_evolution_strategy_registry,
)
from app.domain.intents.evolution.timelines.registry import (
    IntentTimelineRegistry,
    default_timeline_registry,
)
from app.domain.intents.evolution.validation import (
    EvolutionValidator,
    default_evolution_validator,
)
from app.domain.intents.models import IntentDetectionResult

logger = logging.getLogger(__name__)


class IntentEvolutionEngine:
    """
    Primary engine facade for the Intent History & Evolution bounded context.
    """

    def __init__(
        self,
        repository: Optional[IntentEvolutionRepository] = None,
        strategy_registry: Optional[EvolutionStrategyRegistry] = None,
        timeline_registry: Optional[IntentTimelineRegistry] = None,
        validator: Optional[EvolutionValidator] = None,
    ):
        self.repository = repository or default_evolution_repository
        self.strategy_registry = strategy_registry or default_evolution_strategy_registry
        self.timeline_registry = timeline_registry or default_timeline_registry
        self.validator = validator or default_evolution_validator

        self.pipeline = IntentEvolutionPipeline(
            repository=self.repository,
            strategy_registry=self.strategy_registry,
            timeline_registry=self.timeline_registry,
            validator=self.validator,
        )

    def evolve(
        self,
        entity_id: str,
        current_conversation_id: str,
        entity_type: EntityType = EntityType.CUSTOMER,
        workspace_id: Optional[uuid.UUID] = None,
        detection_result: Optional[IntentDetectionResult] = None,
        classification_result: Optional[IntentClassificationResult] = None,
        timeline: Optional[ConversationTimeline] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> IntentEvolutionResult:
        """
        Execute intent evolution for the specified entity and current conversation.
        """
        context = IntentEvolutionContext(
            entity_id=entity_id,
            current_conversation_id=current_conversation_id,
            entity_type=entity_type,
            workspace_id=workspace_id,
            detection_result=detection_result,
            classification_result=classification_result,
            timeline=timeline,
            conversation_metadata=conversation_metadata,
        )

        result = self.pipeline.execute(context)

        if persist and self.repository:
            self.repository.save_evolution_result(result)
            for snap in context.current_snapshots:
                self.repository.save_snapshot(snap)

        return result


default_evolution_engine = IntentEvolutionEngine()
