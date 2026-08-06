"""
HunterOS Engage V1 - Conversation Insight Bounded Context
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Transforms Conversation Analysis and Conversation Timeline outputs into
structured, auditable business insights: Risks, Opportunities, and Action Items.
"""

from app.domain.conversations.insight.classification import (
    InsightClassifier,
    default_insight_classifier,
)
from app.domain.conversations.insight.context import (
    ConversationInsightContext,
    InsightPipelineState,
)
from app.domain.conversations.insight.detectors.actions import (
    AbstractActionItemDetector,
    ActionItemDetectorRegistry,
    CustomActionItemDetector,
    CustomerActionItemDetector,
    InternalTeamActionItemDetector,
    PendingResponseActionItemDetector,
    RequestedDocumentActionItemDetector,
    ScheduledActivityActionItemDetector,
    SharedActionItemDetector,
    default_action_item_detector_registry,
    register_standard_action_item_detectors,
)
from app.domain.conversations.insight.detectors.opportunities import (
    AbstractOpportunityDetector,
    AdditionalRequirementOpportunityDetector,
    CrossSellOpportunityDetector,
    CustomOpportunityDetector,
    DocumentSharingOpportunityDetector,
    FollowUpOpportunityDetector,
    MeetingOpportunityDetector,
    OpportunityDetectorRegistry,
    QualificationOpportunityDetector,
    UpsellOpportunityDetector,
    default_opportunity_detector_registry,
    register_standard_opportunity_detectors,
)
from app.domain.conversations.insight.detectors.risks import (
    AbstractRiskDetector,
    BudgetGapRiskDetector,
    CommunicationGapRiskDetector,
    CustomRiskDetector,
    DelayedResponseRiskDetector,
    MissingDocumentRiskDetector,
    MissingInformationRiskDetector,
    RequirementAmbiguityRiskDetector,
    RiskDetectorRegistry,
    TimelineConflictRiskDetector,
    UnansweredQuestionRiskDetector,
    default_risk_detector_registry,
    register_standard_risk_detectors,
)
from app.domain.conversations.insight.engine import (
    ConversationInsightEngine,
    default_conversation_insight_engine,
)
from app.domain.conversations.insight.models import (
    ActionItemInsight,
    ActionOwnerType,
    ConversationInsight,
    ConversationInsightResult,
    InsightCategory,
    InsightDiagnostics,
    InsightEvidence,
    InsightMetadata,
    InsightPriority,
    InsightScopeType,
    InsightType,
    OpportunityInsight,
    RiskInsight,
)
from app.domain.conversations.insight.repository import (
    InMemoryInsightRepository,
    InsightReadRepository,
    InsightWriteRepository,
    default_insight_repository,
)
from app.domain.conversations.insight.validation import (
    InsightValidationFramework,
    default_insight_validation_framework,
)
from app.domain.conversations.insight.views import (
    AbstractInsightView,
    AuditInsightView,
    ExecutiveInsightView,
    InsightViewRegistry,
    OperationsInsightView,
    SalesInsightView,
    default_insight_view_registry,
    register_standard_insight_views,
)

__all__ = [
    # Engine & Core Aggregates
    "ConversationInsightEngine",
    "default_conversation_insight_engine",
    "ConversationInsightResult",
    "ConversationInsight",
    "RiskInsight",
    "OpportunityInsight",
    "ActionItemInsight",
    "InsightEvidence",
    "InsightMetadata",
    "InsightDiagnostics",
    # Enums
    "InsightType",
    "InsightCategory",
    "InsightPriority",
    "ActionOwnerType",
    "InsightScopeType",
    # Context & State
    "ConversationInsightContext",
    "InsightPipelineState",
    # Risk Detectors
    "AbstractRiskDetector",
    "RiskDetectorRegistry",
    "default_risk_detector_registry",
    "MissingInformationRiskDetector",
    "UnansweredQuestionRiskDetector",
    "MissingDocumentRiskDetector",
    "DelayedResponseRiskDetector",
    "BudgetGapRiskDetector",
    "TimelineConflictRiskDetector",
    "RequirementAmbiguityRiskDetector",
    "CommunicationGapRiskDetector",
    "CustomRiskDetector",
    "register_standard_risk_detectors",
    # Opportunity Detectors
    "AbstractOpportunityDetector",
    "OpportunityDetectorRegistry",
    "default_opportunity_detector_registry",
    "UpsellOpportunityDetector",
    "CrossSellOpportunityDetector",
    "AdditionalRequirementOpportunityDetector",
    "FollowUpOpportunityDetector",
    "DocumentSharingOpportunityDetector",
    "MeetingOpportunityDetector",
    "QualificationOpportunityDetector",
    "CustomOpportunityDetector",
    "register_standard_opportunity_detectors",
    # Action Item Detectors
    "AbstractActionItemDetector",
    "ActionItemDetectorRegistry",
    "default_action_item_detector_registry",
    "CustomerActionItemDetector",
    "InternalTeamActionItemDetector",
    "SharedActionItemDetector",
    "PendingResponseActionItemDetector",
    "RequestedDocumentActionItemDetector",
    "ScheduledActivityActionItemDetector",
    "CustomActionItemDetector",
    "register_standard_action_item_detectors",
    # Classifier & Validator
    "InsightClassifier",
    "default_insight_classifier",
    "InsightValidationFramework",
    "default_insight_validation_framework",
    # Views
    "AbstractInsightView",
    "InsightViewRegistry",
    "default_insight_view_registry",
    "ExecutiveInsightView",
    "SalesInsightView",
    "OperationsInsightView",
    "AuditInsightView",
    "register_standard_insight_views",
    # Repositories
    "InsightWriteRepository",
    "InsightReadRepository",
    "InMemoryInsightRepository",
    "default_insight_repository",
]
