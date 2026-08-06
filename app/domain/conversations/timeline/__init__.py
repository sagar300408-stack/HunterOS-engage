"""
HunterOS Engage V1 - Conversation Intelligence: Conversation Timeline Package
Phase 2.2.2: Conversation Timeline
"""

from app.domain.conversations.timeline.context import ConversationTimelineContext
from app.domain.conversations.timeline.engine import (
    ConversationTimelineEngine,
    default_conversation_timeline_engine,
)
from app.domain.conversations.timeline.extractors import (
    AbstractTimelineEventExtractor,
    TimelineEventExtractorRegistry,
    default_timeline_event_extractor_registry,
)
from app.domain.conversations.timeline.milestones import (
    AbstractMilestoneRule,
    MilestoneRuleRegistry,
    default_milestone_rule_registry,
)
from app.domain.conversations.timeline.models import (
    ConversationEventStream,
    ConversationTimeline,
    ImportantMoment,
    ImportantMomentType,
    MilestoneType,
    TimelineDiagnostics,
    TimelineEvent,
    TimelineEventCategory,
    TimelineEventType,
    TimelineMetadata,
    TimelineMilestone,
    TimelinePipelineState,
    TimelineProvenance,
    TimelineScopeType,
    TimelineViewFormat,
)
from app.domain.conversations.timeline.moments import (
    AbstractImportantMomentRule,
    ImportantMomentRegistry,
    default_important_moment_registry,
)
from app.domain.conversations.timeline.normalizer import (
    TimelineEventNormalizer,
    default_timeline_event_normalizer,
)
from app.domain.conversations.timeline.stages import (
    ChronologicalOrderingStage,
    DetectImportantMomentsStage,
    DetectMilestonesStage,
    ExtractEventsStage,
    LoadAnalysisStage,
    NormalizeTimelineEventsStage,
    OutputTimelineStage,
    TimelinePipelineStage,
    ValidateTimelineStage,
)
from app.domain.conversations.timeline.validation import (
    TimelineValidationError,
    TimelineValidationFramework,
    default_timeline_validation_framework,
)
from app.domain.conversations.timeline.views import (
    AbstractTimelineView,
    ChronologicalEventView,
    ExecutiveSummaryTimelineView,
    ImportantMomentsView,
    MilestoneOnlyView,
    ParticipantSpecificView,
    TimelineViewRegistry,
    default_timeline_view_registry,
)

__all__ = [
    # Engine & Context
    "ConversationTimelineEngine",
    "default_conversation_timeline_engine",
    "ConversationTimelineContext",
    # Models & Enums
    "TimelineEventType",
    "TimelineEventCategory",
    "MilestoneType",
    "ImportantMomentType",
    "TimelineScopeType",
    "TimelineViewFormat",
    "TimelinePipelineState",
    "TimelineProvenance",
    "TimelineEvent",
    "TimelineMilestone",
    "ImportantMoment",
    "ConversationEventStream",
    "TimelineMetadata",
    "TimelineDiagnostics",
    "ConversationTimeline",
    # Extractors
    "AbstractTimelineEventExtractor",
    "TimelineEventExtractorRegistry",
    "default_timeline_event_extractor_registry",
    # Milestones
    "AbstractMilestoneRule",
    "MilestoneRuleRegistry",
    "default_milestone_rule_registry",
    # Moments
    "AbstractImportantMomentRule",
    "ImportantMomentRegistry",
    "default_important_moment_registry",
    # Normalizer & Validation
    "TimelineEventNormalizer",
    "default_timeline_event_normalizer",
    "TimelineValidationFramework",
    "TimelineValidationError",
    "default_timeline_validation_framework",
    # Views
    "AbstractTimelineView",
    "TimelineViewRegistry",
    "default_timeline_view_registry",
    "ChronologicalEventView",
    "MilestoneOnlyView",
    "ImportantMomentsView",
    "ExecutiveSummaryTimelineView",
    "ParticipantSpecificView",
    # Stages
    "TimelinePipelineStage",
    "LoadAnalysisStage",
    "ExtractEventsStage",
    "NormalizeTimelineEventsStage",
    "ChronologicalOrderingStage",
    "DetectMilestonesStage",
    "DetectImportantMomentsStage",
    "ValidateTimelineStage",
    "OutputTimelineStage",
]
