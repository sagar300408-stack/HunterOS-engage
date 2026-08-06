"""
HunterOS Engage V1 - Intent Intelligence: Intent Classification Subsystem
Transforms detected intents into normalized, enriched, relational business knowledge.
"""

from app.domain.intents.classification.api import (
    CanonicalIntentAPIv1,
    IntentClassificationAPIv1,
    canonical_intent_api_v1,
)
from app.domain.intents.classification.canonical.models import (
    CanonicalIntent,
    CanonicalPayload,
)
from app.domain.intents.classification.canonical.normalizer import (
    IntentNormalizer,
    default_intent_normalizer,
)
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.engine import (
    IntentClassificationEngine,
    default_classification_engine,
)
from app.domain.intents.classification.grouping.engine import (
    IntentGroupingEngine,
    default_grouping_engine,
)
from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassificationDiagnostics,
    ClassificationMetadata,
    ClassificationMethod,
    ClassificationProvenance,
    ClassifiedIntent,
    IntentCategory,
    IntentGroup,
    IntentGroupType,
    IntentRelationship,
    IntentRelationshipType,
    IntentClassificationResult,
)
from app.domain.intents.classification.pipeline import (
    IntentClassificationPipeline,
    default_classification_pipeline,
)
from app.domain.intents.classification.plugins.base import IndustryIntentPlugin
from app.domain.intents.classification.plugins.registry import (
    IndustryPluginRegistry,
    default_industry_plugin_registry,
)
from app.domain.intents.classification.process.models import BusinessProcessDefinition
from app.domain.intents.classification.process.registry import (
    BusinessProcessRegistry,
    default_business_process_registry,
)
from app.domain.intents.classification.query import (
    IntentClassificationQueryEngine,
    default_classification_query_engine,
)
from app.domain.intents.classification.relationships.engine import (
    IntentRelationshipEngine,
    default_relationship_engine,
)
from app.domain.intents.classification.relationships.registry import (
    IntentRelationshipRuleRegistry,
    default_relationship_rule_registry,
)
from app.domain.intents.classification.relationships.rules import (
    AbstractRelationshipRule,
    ComplementRelationshipRule,
    ConflictRelationshipRule,
    DependencyRelationshipRule,
    HierarchyRelationshipRule,
    RelatedRelationshipRule,
)
from app.domain.intents.classification.repository import (
    InMemoryIntentClassificationRepository,
    default_classification_repository,
)
from app.domain.intents.classification.rules.base import (
    AbstractClassificationRule,
    AbstractClassificationRulePack,
    ClassificationCandidate,
)
from app.domain.intents.classification.rules.packs.core import (
    CoreClassificationRulePack,
)
from app.domain.intents.classification.rules.packs.healthcare import (
    HealthcareClassificationRulePack,
)
from app.domain.intents.classification.rules.packs.real_estate import (
    RealEstateClassificationRulePack,
)
from app.domain.intents.classification.rules.registry import (
    ClassificationRuleRegistry,
    default_classification_rule_registry,
)
from app.domain.intents.classification.taxonomy.graph import (
    BusinessIntentTaxonomyGraph,
    TaxonomyPath,
    default_taxonomy_graph,
)
from app.domain.intents.classification.taxonomy.models import (
    TaxonomyEdge,
    TaxonomyNode,
)
from app.domain.intents.classification.validation import (
    IntentClassificationValidator,
    default_classification_validator,
)
from app.domain.intents.classification.views.audit import AuditClassificationView
from app.domain.intents.classification.views.base import AbstractClassificationView
from app.domain.intents.classification.views.executive import (
    ExecutiveClassificationView,
)
from app.domain.intents.classification.views.operations import (
    OperationsClassificationView,
)
from app.domain.intents.classification.views.sales import SalesClassificationView

__all__ = [
    # API & Engines
    "CanonicalIntentAPIv1",
    "IntentClassificationAPIv1",
    "canonical_intent_api_v1",
    "IntentClassificationEngine",
    "default_classification_engine",
    "IntentClassificationPipeline",
    "default_classification_pipeline",
    "IntentClassificationContext",
    # Models
    "IntentCategory",
    "BusinessDomain",
    "IntentRelationshipType",
    "IntentGroupType",
    "ClassificationMethod",
    "ClassifiedIntent",
    "IntentRelationship",
    "IntentGroup",
    "ClassificationMetadata",
    "ClassificationDiagnostics",
    "ClassificationProvenance",
    "IntentClassificationResult",
    # Canonical
    "CanonicalIntent",
    "CanonicalPayload",
    "IntentNormalizer",
    "default_intent_normalizer",
    # Taxonomy Graph
    "TaxonomyNode",
    "TaxonomyEdge",
    "TaxonomyPath",
    "BusinessIntentTaxonomyGraph",
    "default_taxonomy_graph",
    # Process
    "BusinessProcessDefinition",
    "BusinessProcessRegistry",
    "default_business_process_registry",
    # Relationships
    "AbstractRelationshipRule",
    "DependencyRelationshipRule",
    "ConflictRelationshipRule",
    "ComplementRelationshipRule",
    "HierarchyRelationshipRule",
    "RelatedRelationshipRule",
    "IntentRelationshipRuleRegistry",
    "default_relationship_rule_registry",
    "IntentRelationshipEngine",
    "default_relationship_engine",
    # Grouping
    "IntentGroupingEngine",
    "default_grouping_engine",
    # Rules
    "AbstractClassificationRule",
    "AbstractClassificationRulePack",
    "ClassificationCandidate",
    "CoreClassificationRulePack",
    "RealEstateClassificationRulePack",
    "HealthcareClassificationRulePack",
    "ClassificationRuleRegistry",
    "default_classification_rule_registry",
    # Plugins
    "IndustryIntentPlugin",
    "IndustryPluginRegistry",
    "default_industry_plugin_registry",
    # Validation
    "IntentClassificationValidator",
    "default_classification_validator",
    # CQRS
    "InMemoryIntentClassificationRepository",
    "default_classification_repository",
    "IntentClassificationQueryEngine",
    "default_classification_query_engine",
    # Views
    "AbstractClassificationView",
    "ExecutiveClassificationView",
    "SalesClassificationView",
    "OperationsClassificationView",
    "AuditClassificationView",
]
