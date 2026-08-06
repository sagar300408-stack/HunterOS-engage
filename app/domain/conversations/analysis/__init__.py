"""
HunterOS Engage — Conversation Analysis Bounded Context (Phase 2.2.1)

Public package exports for Conversation Analysis.
"""

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.engine import (
    ConversationAnalysisEngine,
    default_conversation_analysis_engine,
)
from app.domain.conversations.analysis.engines import (
    ConversationMetadataExtractor,
    ConversationSummaryEngine,
    KeyFactExtractionEngine,
    TopicDetectionEngine,
)
from app.domain.conversations.analysis.models import (
    AnalysisDiagnostics,
    ArtifactProvenance,
    CanonicalValue,
    ConversationAnalysisResult,
    ConversationMetadata,
    ConversationSegment,
    ConversationSummary,
    ExtractedFact,
    ExtractionMethod,
    FactCategory,
    MessageDirection,
    NormalizedMessage,
    PipelineState,
    SegmentType,
    SourceMessageRef,
    SummaryType,
    TopicAnalysis,
    TopicDistribution,
    TopicTimelineItem,
)
from app.domain.conversations.analysis.normalizer import (
    FactNormalizer,
    default_fact_normalizer,
)
from app.domain.conversations.analysis.pipeline import ConversationPipelineRunner
from app.domain.conversations.analysis.registry import (
    AnalysisArtifactDescriptor,
    AnalysisArtifactRegistry,
    SummaryTemplateRegistry,
    default_analysis_artifact_registry,
    default_summary_template_registry,
)
from app.domain.conversations.analysis.repository import (
    AbstractConversationAnalysisReadRepository,
    AbstractConversationAnalysisWriteRepository,
    InMemoryConversationAnalysisReadRepository,
    InMemoryConversationAnalysisWriteRepository,
)
from app.domain.conversations.analysis.router import (
    router as conversation_analysis_router,
)
from app.domain.conversations.analysis.segmentation import (
    ConversationSegmentationEngine,
)
from app.domain.conversations.analysis.stages import (
    FactExtractionStage,
    FactNormalizationStage,
    LoadStage,
    NormalizeStage,
    OutputStage,
    PipelineStage,
    SegmentStage,
    SummaryStage,
    TopicStage,
    ValidationStage,
)
from app.domain.conversations.analysis.taxonomy import (
    TopicTaxonomy,
    TopicTaxonomyNode,
    default_topic_taxonomy,
)
from app.domain.conversations.analysis.validation import (
    AnalysisValidationFramework,
)

__all__ = [
    # Models & Enums
    "SegmentType",
    "FactCategory",
    "SummaryType",
    "ExtractionMethod",
    "MessageDirection",
    "PipelineState",
    "SourceMessageRef",
    "ArtifactProvenance",
    "CanonicalValue",
    "NormalizedMessage",
    "ConversationSegment",
    "TopicDistribution",
    "TopicTimelineItem",
    "TopicAnalysis",
    "ExtractedFact",
    "ConversationSummary",
    "ConversationMetadata",
    "AnalysisDiagnostics",
    "ConversationAnalysisResult",
    # Context
    "ConversationAnalysisContext",
    # Taxonomy
    "TopicTaxonomy",
    "TopicTaxonomyNode",
    "default_topic_taxonomy",
    # Registries
    "AnalysisArtifactDescriptor",
    "AnalysisArtifactRegistry",
    "SummaryTemplateRegistry",
    "default_analysis_artifact_registry",
    "default_summary_template_registry",
    # Normalizer
    "FactNormalizer",
    "default_fact_normalizer",
    # Segmentation & Validation
    "ConversationSegmentationEngine",
    "AnalysisValidationFramework",
    # Engines
    "TopicDetectionEngine",
    "KeyFactExtractionEngine",
    "ConversationSummaryEngine",
    "ConversationMetadataExtractor",
    # Stages & Pipeline
    "PipelineStage",
    "LoadStage",
    "NormalizeStage",
    "SegmentStage",
    "TopicStage",
    "FactExtractionStage",
    "FactNormalizationStage",
    "SummaryStage",
    "ValidationStage",
    "OutputStage",
    "ConversationPipelineRunner",
    # Repositories
    "AbstractConversationAnalysisReadRepository",
    "AbstractConversationAnalysisWriteRepository",
    "InMemoryConversationAnalysisReadRepository",
    "InMemoryConversationAnalysisWriteRepository",
    # Facade & Router
    "ConversationAnalysisEngine",
    "default_conversation_analysis_engine",
    "conversation_analysis_router",
]
