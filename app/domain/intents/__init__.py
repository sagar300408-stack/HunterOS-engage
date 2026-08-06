"""
HunterOS Engage V1 - Intent Intelligence Module
Bounded context for deterministic intent detection, taxonomy hierarchy, evidence tracing, and view projections.
"""

from app.domain.intents.api import (
    IntentDetectionAPIv1,
    intent_api_v1,
)
from app.domain.intents.context import (
    IntentDetectionContext,
    IntentPipelineState,
)
from app.domain.intents.engine import (
    IntentDetectionEngine,
    default_intent_detection_engine,
)
from app.domain.intents.models import (
    BusinessImportance,
    DetectedIntent,
    EvidenceEdge,
    EvidenceNode,
    EvidenceNodeType,
    IntentDetectionMethod,
    IntentDetectionResult,
    IntentDiagnostics,
    IntentEvidence,
    IntentEvidenceGraph,
    IntentMetadata,
    IntentProvenance,
    IntentTaxonomyCategory,
    IntentType,
    RuleExecutionReport,
)
from app.domain.intents.pipeline import IntentPipelineRunner
from app.domain.intents.providers.base import IntentDetectorProvider
from app.domain.intents.providers.rule_based import RuleBasedIntentDetectorProvider
from app.domain.intents.query import (
    IntentQueryEngine,
    default_intent_query_engine,
)
from app.domain.intents.recognizer import IntentRecognizer
from app.domain.intents.repository import (
    InMemoryIntentRepository,
    IntentRepository,
    default_intent_repository,
)
from app.domain.intents.resolver import (
    IntentResolver,
    default_intent_resolver,
)
from app.domain.intents.rules.base import AbstractIntentRule
from app.domain.intents.rules.pack import AbstractRulePack
from app.domain.intents.rules.packs.core import CoreRulePack
from app.domain.intents.rules.packs.real_estate import RealEstateRulePack
from app.domain.intents.rules.registry import (
    IntentRulePackRegistry,
    default_rule_pack_registry,
)
from app.domain.intents.taxonomy import (
    IntentTaxonomy,
    TaxonomyNode,
)
from app.domain.intents.validation import (
    IntentValidator,
    default_intent_validator,
)
from app.domain.intents.views.base import AbstractIntentView
from app.domain.intents.views.registry import (
    IntentViewRegistry,
    default_intent_view_registry,
)
from app.domain.intents.views.standard import (
    AuditIntentView,
    ExecutiveIntentView,
    OperationsIntentView,
    SalesIntentView,
)

__all__ = [
    # Core Domain Models
    "IntentType",
    "IntentTaxonomyCategory",
    "BusinessImportance",
    "IntentDetectionMethod",
    "EvidenceNodeType",
    "EvidenceNode",
    "EvidenceEdge",
    "IntentEvidenceGraph",
    "IntentEvidence",
    "IntentProvenance",
    "RuleExecutionReport",
    "DetectedIntent",
    "IntentMetadata",
    "IntentDiagnostics",
    "IntentDetectionResult",
    # Taxonomy
    "TaxonomyNode",
    "IntentTaxonomy",
    # Context & State Machine
    "IntentPipelineState",
    "IntentDetectionContext",
    # Recognition, Validation, Resolution
    "IntentRecognizer",
    "IntentValidator",
    "default_intent_validator",
    "IntentResolver",
    "default_intent_resolver",
    # Providers
    "IntentDetectorProvider",
    "RuleBasedIntentDetectorProvider",
    # Rules & Packs
    "AbstractIntentRule",
    "AbstractRulePack",
    "CoreRulePack",
    "RealEstateRulePack",
    "IntentRulePackRegistry",
    "default_rule_pack_registry",
    # Pipeline
    "IntentPipelineRunner",
    # Views & Projections
    "AbstractIntentView",
    "ExecutiveIntentView",
    "SalesIntentView",
    "OperationsIntentView",
    "AuditIntentView",
    "IntentViewRegistry",
    "default_intent_view_registry",
    # CQRS Storage & Queries
    "IntentRepository",
    "InMemoryIntentRepository",
    "default_intent_repository",
    "IntentQueryEngine",
    "default_intent_query_engine",
    # Facade & Public API
    "IntentDetectionEngine",
    "default_intent_detection_engine",
    "IntentDetectionAPIv1",
    "intent_api_v1",
]
