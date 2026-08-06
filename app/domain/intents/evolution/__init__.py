"""
HunterOS Engage V1 - Intent History & Evolution Bounded Context
Temporal intelligence layer recording intent lifecycles, state transitions, velocity, and event streams.
"""

from app.domain.intents.evolution.api import (
    IntentEvolutionAPIv1,
    intent_evolution_api_v1,
)
from app.domain.intents.evolution.engine import (
    IntentEvolutionEngine,
    default_evolution_engine,
)
from app.domain.intents.evolution.models import (
    EntityType,
    EvolutionDiagnostics,
    EvolutionMetadata,
    EvolutionProvenance,
    IntentEvolutionEvent,
    IntentEvolutionEventStream,
    IntentEvolutionEventType,
    IntentEvolutionResult,
    IntentHistory,
    IntentLifecycleState,
    IntentStateSnapshot,
    IntentStateTransition,
    IntentTimeline,
    IntentVelocity,
)
from app.domain.intents.evolution.pipeline import IntentEvolutionPipeline
from app.domain.intents.evolution.query import (
    IntentEvolutionQuery,
    default_evolution_query,
)
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

__all__ = [
    "EntityType",
    "IntentLifecycleState",
    "IntentEvolutionEventType",
    "IntentVelocity",
    "EvolutionProvenance",
    "IntentStateSnapshot",
    "IntentStateTransition",
    "IntentEvolutionEvent",
    "IntentEvolutionEventStream",
    "IntentTimeline",
    "IntentHistory",
    "EvolutionMetadata",
    "EvolutionDiagnostics",
    "IntentEvolutionResult",
    "IntentEvolutionPipeline",
    "IntentEvolutionEngine",
    "default_evolution_engine",
    "IntentEvolutionRepository",
    "default_evolution_repository",
    "IntentEvolutionQuery",
    "default_evolution_query",
    "IntentEvolutionAPIv1",
    "intent_evolution_api_v1",
    "EvolutionStrategyRegistry",
    "default_evolution_strategy_registry",
    "IntentTimelineRegistry",
    "default_timeline_registry",
]
