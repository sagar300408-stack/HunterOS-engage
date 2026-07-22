"""
conftest.py for friction tests.

Pre-imports all SQLAlchemy models in dependency order so that
the mapper configuration succeeds before any test runs.
This prevents the "IntentHistory not defined" mapper error
that occurs when models are imported in isolation.
"""
import pytest

# ── Import all models in correct order ────────────────────────────────────────
# Base and foundation models first
from app.domain.conversations.models import Base, Conversation, Message   # noqa: F401
from app.domain.customers.models import Customer                          # noqa: F401
from app.domain.intent.models import IntentHistory                        # noqa: F401
from app.domain.security.models import User, AuditLog                   # noqa: F401
from app.domain.memory.models import CustomerMemory, CustomerMemoryEvent  # noqa: F401
from app.domain.followup.models import FollowUpQueue, FollowUpExecution  # noqa: F401

# Friction domain models
from app.domain.friction.models import (                                  # noqa: F401
    FrictionEvent, SLAPolicy,
    FrictionScoreSnapshot, WorkflowStageLatency,
)

# Recommendation model (used by FrictionRecommendationEngine)
from app.domain.recommendation.models import RecommendationSnapshot       # noqa: F401

# Intelligence domain models
from app.domain.intelligence.models import (                              # noqa: F401
    OperationalHealthSnapshot,
    OpportunityLeakageEvent,
    RootCauseAnalysis,
    PredictionEvent,
    ExecutiveInsight,
    ObservationDebounce,
)

# Collaboration domain models
from app.domain.collaboration.models import (                             # noqa: F401
    ActionableIntent,
    CollaborationTask,
    AutonomyPolicy,
    TaskApprovalChain,
    DecisionAuditLog,
    DecisionExplanation,
    TaskEscalation,
    TaskFeedback,
    LearningRule,
)

# Impact domain models
from app.domain.impact.models import (                                    # noqa: F401
    FinancialConfig,
    BusinessTargets,
    BaselineMetrics,
    ImpactEvent,
    EvidenceTrace,
    ValueAttribution,
    ExecutiveImpactReport,
)

# Context domain models
from app.domain.context.models import (                                   # noqa: F401
    OrganizationNode,
    ProductService,
    WorkflowDefinition,
    BusinessPolicy,
    CustomerContext,
    TeamMemberContext,
    KnowledgeDocument,
    BusinessOntology,
    KnowledgeGraphEdge,
    ContextConflict
)

# Onboarding domain models
from app.domain.onboarding.models import (                                # noqa: F401
    WorkspaceProvisioning,
    OnboardingIntegrationConnection,
    ImportJob,
    ValidationResult,
    GoLiveAssessment,
    OperationalCapabilityMatrix,
    WorkspaceMaturity
)

# UI domain models
from app.domain.ui.models import (                                        # noqa: F401
    UserPreference,
    NotificationPreference,
    DashboardDefinition,
    NavigationNode,
    FeatureFlag,
    UXAnalyticsEvent
)
