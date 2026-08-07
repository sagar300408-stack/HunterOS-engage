"""
HunterOS Engage V1 - Multi-Intent Resolution Package
Bounded Context for resolving overlapping, competing, dependent, and hierarchical intents.
"""

from app.domain.intents.resolution.api_v1 import (
    IntentResolutionAPIv1,
    intent_resolution_api_v1,
)
from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.engine import MultiIntentResolutionEngine
from app.domain.intents.resolution.models import (
    DominanceFactor,
    DominantIntent,
    GraphSnapshot,
    IntentConflict,
    IntentConflictSeverity,
    IntentConflictType,
    IntentDependency,
    IntentDependencyType,
    IntentNode,
    IntentRelationship,
    IntentRelationshipType,
    IntentResolutionGraph,
    IntentResolutionGroup,
    MultiIntentResolutionResult,
    ResolutionDiagnostics,
    ResolutionMetadata,
    ResolutionProvenance,
    ResolutionStatus,
)
from app.domain.intents.resolution.pipeline import MultiIntentResolutionPipeline
from app.domain.intents.resolution.registry import (
    IntentResolutionRegistry,
    default_resolution_registry,
)
from app.domain.intents.resolution.repository import (
    ResolutionRepository,
    default_resolution_repository,
)
from app.domain.intents.resolution.schemas import (
    ConflictFilterParams,
    DependencyFilterParams,
    DominantIntentDTO,
    GraphSnapshotDTO,
    GroupFilterParams,
    IntentConflictDTO,
    IntentDependencyDTO,
    IntentNodeDTO,
    IntentRelationshipDTO,
    IntentResolutionAnalyticsDTO,
    IntentResolutionGraphDTO,
    IntentResolutionGroupDTO,
    MultiIntentResolutionResponse,
    RelationshipFilterParams,
    ResolutionDiagnosticsDTO,
    ResolutionMetadataDTO,
    ResolutionProvenanceDTO,
    ResolveIntentsRequest,
)
from app.domain.intents.resolution.validation import (
    MultiIntentResolutionValidator,
    ResolutionValidationError,
)

__all__ = [
    # Public API
    "IntentResolutionAPIv1",
    "intent_resolution_api_v1",
    # Engine & Pipeline
    "MultiIntentResolutionEngine",
    "MultiIntentResolutionPipeline",
    "MultiIntentResolutionContext",
    # Registry & Repository
    "IntentResolutionRegistry",
    "default_resolution_registry",
    "ResolutionRepository",
    "default_resolution_repository",
    # Validation
    "MultiIntentResolutionValidator",
    "ResolutionValidationError",
    # Domain Models
    "IntentResolutionGraph",
    "IntentNode",
    "IntentRelationship",
    "IntentRelationshipType",
    "IntentConflict",
    "IntentConflictType",
    "IntentConflictSeverity",
    "IntentDependency",
    "IntentDependencyType",
    "DominantIntent",
    "DominanceFactor",
    "IntentResolutionGroup",
    "ResolutionStatus",
    "GraphSnapshot",
    "ResolutionMetadata",
    "ResolutionDiagnostics",
    "ResolutionProvenance",
    "MultiIntentResolutionResult",
    # Public DTOs
    "IntentNodeDTO",
    "IntentRelationshipDTO",
    "IntentConflictDTO",
    "IntentDependencyDTO",
    "DominantIntentDTO",
    "IntentResolutionGraphDTO",
    "GraphSnapshotDTO",
    "IntentResolutionGroupDTO",
    "ResolutionMetadataDTO",
    "ResolutionDiagnosticsDTO",
    "ResolutionProvenanceDTO",
    "IntentResolutionAnalyticsDTO",
    "MultiIntentResolutionResponse",
    "ResolveIntentsRequest",
    "GroupFilterParams",
    "RelationshipFilterParams",
    "ConflictFilterParams",
    "DependencyFilterParams",
]
