"""
HunterOS Engage — Memory Context & Intelligence Integration Package (Phase 2.1.5)
"""

from app.domain.memory.intelligence.cache import (
    AbstractContextCache,
    InMemoryContextCache,
    NoOpContextCache,
)
from app.domain.memory.intelligence.composer import ContextComposer
from app.domain.memory.intelligence.export import (
    ContextExportEngine,
    default_context_export_engine,
)
from app.domain.memory.intelligence.gateway import (
    MemoryContextGateway,
    get_memory_context_gateway,
    set_memory_context_gateway,
)
from app.domain.memory.intelligence.models import (
    ComposedContext,
    ContextBlock,
    ContextBlockType,
    ContextCompletenessReport,
    ContextCompletenessStatus,
    ContextLineage,
    ContextMetadata,
    ContextScope,
    ExportTargetFormat,
)
from app.domain.memory.intelligence.pipeline import ContextPipeline
from app.domain.memory.intelligence.registry import (
    ContextDescriptor,
    ContextSchemaRegistry,
    default_context_schema_registry,
)
from app.domain.memory.intelligence.router import router as context_router
from app.domain.memory.intelligence.schemas import (
    ContextCompletenessResponse,
    ContextLineageResponse,
    ContextMetadataResponse,
    ContextRequestOptions,
    CustomContextRequest,
    CustomContextResponse,
    CustomerContextResponse,
    DashboardContextExportDTO,
    ExecutiveContextExportDTO,
    ExecutiveContextResponse,
    OpportunityContextResponse,
    OrganizationContextResponse,
    PropertyContextResponse,
    StructuredContextDTO,
)
from app.domain.memory.intelligence.strategies import (
    CompositionStrategyRegistry,
    ContextCompositionStrategy,
    Customer360CompositionStrategy,
    ExecutiveCompositionStrategy,
    OpportunityCompositionStrategy,
    OrganizationCompositionStrategy,
    PropertyCompositionStrategy,
    SelectiveCompositionStrategy,
    default_strategy_registry,
)
from app.domain.memory.intelligence.validation import (
    ContextValidationError,
    ContextValidator,
    CrossWorkspaceContextError,
    MissingRequiredContextError,
    default_context_validator,
)

__all__ = [
    # Gateway & Router
    "MemoryContextGateway",
    "get_memory_context_gateway",
    "set_memory_context_gateway",
    "context_router",
    # Composer & Pipeline
    "ContextComposer",
    "ContextPipeline",
    "ContextExportEngine",
    "default_context_export_engine",
    # Models & Enums
    "ComposedContext",
    "ContextBlock",
    "ContextBlockType",
    "ContextCompletenessReport",
    "ContextCompletenessStatus",
    "ContextLineage",
    "ContextMetadata",
    "ContextScope",
    "ExportTargetFormat",
    # Registry & Strategies
    "ContextDescriptor",
    "ContextSchemaRegistry",
    "default_context_schema_registry",
    "ContextCompositionStrategy",
    "Customer360CompositionStrategy",
    "OrganizationCompositionStrategy",
    "OpportunityCompositionStrategy",
    "PropertyCompositionStrategy",
    "ExecutiveCompositionStrategy",
    "SelectiveCompositionStrategy",
    "CompositionStrategyRegistry",
    "default_strategy_registry",
    # Cache & Validation
    "AbstractContextCache",
    "InMemoryContextCache",
    "NoOpContextCache",
    "ContextValidator",
    "default_context_validator",
    "ContextValidationError",
    "CrossWorkspaceContextError",
    "MissingRequiredContextError",
    # Schemas / DTOs
    "ContextMetadataResponse",
    "ContextLineageResponse",
    "ContextCompletenessResponse",
    "ContextRequestOptions",
    "CustomContextRequest",
    "CustomerContextResponse",
    "OrganizationContextResponse",
    "OpportunityContextResponse",
    "PropertyContextResponse",
    "ExecutiveContextResponse",
    "CustomContextResponse",
    "ExecutiveContextExportDTO",
    "DashboardContextExportDTO",
    "StructuredContextDTO",
]
