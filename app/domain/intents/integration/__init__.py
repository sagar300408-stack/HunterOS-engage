"""
HunterOS Engage V1 - Intent Intelligence Integration Domain Package
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Public Exports for Intent Intelligence Platform, Gateway, Context Assembler,
Composition Profiles, Graph, and Frozen API v1.
"""

from app.domain.intents.integration.api_v1 import (
    IntentIntelligenceAPIv1,
    intent_intelligence_api_v1,
)
from app.domain.intents.integration.assembler import IntentContextAssembler
from app.domain.intents.integration.cache import (
    IIntentContextCache,
    InMemoryIntentContextCache,
    NullIntentContextCache,
)
from app.domain.intents.integration.engines.composition import IntentCompositionEngine
from app.domain.intents.integration.engines.export import IntentExportEngine
from app.domain.intents.integration.engines.query import IntentQueryEngine
from app.domain.intents.integration.gateway import (
    IntentIntelligenceGateway,
    default_intent_gateway,
)
from app.domain.intents.integration.graph import IntentContextGraphBuilder
from app.domain.intents.integration.models import (
    AuditIntentContext,
    CompositionProfileType,
    ContextCompletenessReport,
    ContextDiagnostics,
    ContextGraphLink,
    ContextGraphLinkType,
    ContextGraphNode,
    ContextMetadata,
    ContextProvenance,
    CustomIntentContext,
    ExecutiveIntentContext,
    IntentContextAnalytics,
    IntentContextGraph,
    IntentIntelligenceContext,
    OperationsIntentContext,
    SalesIntentContext,
)
from app.domain.intents.integration.pipeline import IntentIntegrationPipeline
from app.domain.intents.integration.platform import (
    IntentIntelligencePlatform,
    default_intent_platform,
)
from app.domain.intents.integration.profiles import (
    AuditProfile,
    ClassificationProfile,
    CompositionProfile,
    CustomProfile,
    EvolutionProfile,
    ExecutiveProfile,
    FullProfile,
    MinimalProfile,
    OperationsProfile,
    ResolutionProfile,
    SalesProfile,
)
from app.domain.intents.integration.registry import (
    IntentContextRegistry,
    IntentIntelligencePlugin,
    default_context_registry,
)
from app.domain.intents.integration.repository import (
    IntentContextRepository,
    default_context_repository,
)
from app.domain.intents.integration.schemas import (
    AuditIntentContextDTO,
    ContextCompletenessReportDTO,
    ContextDiagnosticsDTO,
    ContextGraphLinkDTO,
    ContextGraphNodeDTO,
    ContextMetadataDTO,
    ContextProvenanceDTO,
    CustomIntentContextDTO,
    DashboardIntentContextDTO,
    ExecutiveIntentContextDTO,
    ExecutiveIntentDTO,
    IntegrateIntentsRequest,
    IntentContextAnalyticsDTO,
    IntentContextGraphDTO,
    IntentIntelligenceContextDTO,
    IntentIntelligenceResponse,
    OperationsIntentContextDTO,
    QueryIntentContextRequest,
    SalesIntentContextDTO,
    StandardAPIIntentContextDTO,
    StructuredIntentContextDTO,
)
from app.domain.intents.integration.validation import IntentContextValidator

__all__ = [
    # API & Platform
    "IntentIntelligenceAPIv1",
    "intent_intelligence_api_v1",
    "IntentIntelligencePlatform",
    "default_intent_platform",
    "IntentIntelligenceGateway",
    "default_intent_gateway",
    "IntentContextAssembler",
    "IntentIntegrationPipeline",
    # Engines
    "IntentCompositionEngine",
    "IntentQueryEngine",
    "IntentExportEngine",
    # Graph & Analytics
    "IntentContextGraphBuilder",
    "IntentContextValidator",
    # Registry & Cache
    "IntentContextRegistry",
    "default_context_registry",
    "IntentIntelligencePlugin",
    "IIntentContextCache",
    "InMemoryIntentContextCache",
    "NullIntentContextCache",
    "IntentContextRepository",
    "default_context_repository",
    # Models
    "IntentIntelligenceContext",
    "IntentContextGraph",
    "ContextGraphNode",
    "ContextGraphLink",
    "ContextGraphLinkType",
    "CompositionProfileType",
    "ContextMetadata",
    "ContextProvenance",
    "ContextDiagnostics",
    "ContextCompletenessReport",
    "IntentContextAnalytics",
    "ExecutiveIntentContext",
    "SalesIntentContext",
    "OperationsIntentContext",
    "AuditIntentContext",
    "CustomIntentContext",
    # Profiles
    "CompositionProfile",
    "MinimalProfile",
    "ClassificationProfile",
    "EvolutionProfile",
    "ResolutionProfile",
    "FullProfile",
    "ExecutiveProfile",
    "SalesProfile",
    "OperationsProfile",
    "AuditProfile",
    "CustomProfile",
    # Schemas
    "IntentIntelligenceContextDTO",
    "IntentIntelligenceResponse",
    "IntegrateIntentsRequest",
    "QueryIntentContextRequest",
    "ContextMetadataDTO",
    "ContextProvenanceDTO",
    "ContextDiagnosticsDTO",
    "ContextCompletenessReportDTO",
    "IntentContextAnalyticsDTO",
    "IntentContextGraphDTO",
    "ContextGraphNodeDTO",
    "ContextGraphLinkDTO",
    "ExecutiveIntentContextDTO",
    "SalesIntentContextDTO",
    "OperationsIntentContextDTO",
    "AuditIntentContextDTO",
    "CustomIntentContextDTO",
    "DashboardIntentContextDTO",
    "ExecutiveIntentDTO",
    "StructuredIntentContextDTO",
    "StandardAPIIntentContextDTO",
]
