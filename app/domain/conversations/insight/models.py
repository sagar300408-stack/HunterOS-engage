"""
HunterOS Engage V1 - Conversation Insight Domain Models
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Defines immutable domain models, enums, evidence traceability,
structured insights (Risks, Opportunities, Action Items), and the ConversationInsightResult aggregate root.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class InsightType(str, Enum):
    """Primary categorization of conversational insight."""
    RISK = "RISK"
    OPPORTUNITY = "OPPORTUNITY"
    ACTION_ITEM = "ACTION_ITEM"
    CUSTOM = "CUSTOM"


class InsightPriority(str, Enum):
    """
    Descriptive severity/prominence of observed conversation evidence.
    NOTE: Must not represent prescriptive business advice or autonomous recommendations.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionOwnerType(str, Enum):
    """Entity responsible for the detected action item."""
    CUSTOMER = "CUSTOMER"
    INTERNAL_TEAM = "INTERNAL_TEAM"
    SHARED = "SHARED"


class InsightScopeType(str, Enum):
    """Scope of insight evaluation."""
    CONVERSATION = "CONVERSATION"
    CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
    ORGANIZATION = "ORGANIZATION"


class InsightCategory(str, Enum):
    """Granular categorization for risks, opportunities, and action items."""
    # ── Risk Categories ───────────────────────────────────────────────────────
    MISSING_INFORMATION = "MISSING_INFORMATION"
    UNANSWERED_QUESTION = "UNANSWERED_QUESTION"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    DELAYED_RESPONSE = "DELAYED_RESPONSE"
    BUDGET_GAP = "BUDGET_GAP"
    TIMELINE_CONFLICT = "TIMELINE_CONFLICT"
    REQUIREMENT_AMBIGUITY = "REQUIREMENT_AMBIGUITY"
    COMMUNICATION_GAP = "COMMUNICATION_GAP"
    CUSTOM_RISK = "CUSTOM_RISK"

    # ── Opportunity Categories ────────────────────────────────────────────────
    UPSELL = "UPSELL"
    CROSS_SELL = "CROSS_SELL"
    ADDITIONAL_REQUIREMENT = "ADDITIONAL_REQUIREMENT"
    FOLLOW_UP = "FOLLOW_UP"
    DOCUMENT_SHARING = "DOCUMENT_SHARING"
    MEETING = "MEETING"
    QUALIFICATION = "QUALIFICATION"
    CUSTOM_OPPORTUNITY = "CUSTOM_OPPORTUNITY"

    # ── Action Item Categories ────────────────────────────────────────────────
    CUSTOMER_ACTION = "CUSTOMER_ACTION"
    INTERNAL_TEAM_ACTION = "INTERNAL_TEAM_ACTION"
    SHARED_ACTION = "SHARED_ACTION"
    PENDING_RESPONSE = "PENDING_RESPONSE"
    REQUESTED_DOCUMENT = "REQUESTED_DOCUMENT"
    SCHEDULED_ACTIVITY = "SCHEDULED_ACTIVITY"
    CUSTOM_ACTION = "CUSTOM_ACTION"


# ── Traceability & Evidence ───────────────────────────────────────────────────

class InsightEvidence(BaseModel):
    """
    Complete bidirectional lineage provenance linking an insight to upstream artifacts.
    No insight may exist without supporting evidence.
    """
    model_config = ConfigDict(frozen=True)

    source_message_ids: List[str] = Field(default_factory=list)
    source_event_ids: List[uuid.UUID] = Field(default_factory=list)
    source_milestone_ids: List[uuid.UUID] = Field(default_factory=list)
    source_moment_ids: List[uuid.UUID] = Field(default_factory=list)
    fact_ids: List[uuid.UUID] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    text_snippets: List[str] = Field(default_factory=list)
    extraction_method: str = "DETERMINISTIC_EVIDENCE"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ── Structured Insight Entities ───────────────────────────────────────────────

class RiskInsight(BaseModel):
    """
    Descriptive business risk identified from conversation artifacts.
    Describes observed gaps, conflicts, or missing prerequisites.
    """
    model_config = ConfigDict(frozen=True)

    risk_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    category: InsightCategory
    title: str
    description: str
    impact_description: Optional[str] = None
    evidence: InsightEvidence
    priority: InsightPriority = InsightPriority.MEDIUM
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OpportunityInsight(BaseModel):
    """
    Descriptive commercial or operational opportunity observed in conversation.
    Describes potential expansion, meeting, or document sharing possibilities.
    """
    model_config = ConfigDict(frozen=True)

    opportunity_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    category: InsightCategory
    title: str
    description: str
    value_potential: Optional[str] = None
    qualification_criteria: List[str] = Field(default_factory=list)
    evidence: InsightEvidence
    priority: InsightPriority = InsightPriority.MEDIUM
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActionItemInsight(BaseModel):
    """
    Explicit or directly implied action item originating strictly from conversation evidence.
    """
    model_config = ConfigDict(frozen=True)

    action_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    category: InsightCategory
    owner_type: ActionOwnerType
    title: str
    description: str
    due_date_hint: Optional[str] = None
    evidence: InsightEvidence
    priority: InsightPriority = InsightPriority.MEDIUM
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationInsight(BaseModel):
    """
    Polymorphic wrapper unifying all insight items for generic filtering and projection.
    """
    model_config = ConfigDict(frozen=True)

    insight_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    insight_type: InsightType
    category: InsightCategory
    title: str
    description: str
    priority: InsightPriority
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: InsightEvidence
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Metadata & Diagnostics ───────────────────────────────────────────────────

class InsightMetadata(BaseModel):
    """High-level metadata summarizing insight generation results."""
    model_config = ConfigDict(frozen=True)

    insight_result_id: uuid.UUID
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    scope_type: InsightScopeType = InsightScopeType.CONVERSATION
    total_insights: int = 0
    total_risks: int = 0
    total_opportunities: int = 0
    total_action_items: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    schema_version: str = "1.0.0"
    generator_version: str = "2.2.3"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InsightDiagnostics(BaseModel):
    """Audit and diagnostic metrics for pipeline execution."""
    model_config = ConfigDict(frozen=True)

    pipeline_execution_time_ms: float = 0.0
    stage_timings_ms: Dict[str, float] = Field(default_factory=dict)
    stages_executed: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    is_valid: bool = True


# ── Aggregate Root ────────────────────────────────────────────────────────────

class ConversationInsightResult(BaseModel):
    """
    Immutable aggregate root representing the complete structured business insights
    synthesized from Conversation Analysis and Conversation Timeline artifacts.
    """
    model_config = ConfigDict(frozen=True)

    insight_result_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    scope_type: InsightScopeType = InsightScopeType.CONVERSATION
    metadata: InsightMetadata
    risks: List[RiskInsight] = Field(default_factory=list)
    opportunities: List[OpportunityInsight] = Field(default_factory=list)
    action_items: List[ActionItemInsight] = Field(default_factory=list)
    all_insights: List[ConversationInsight] = Field(default_factory=list)
    diagnostics: InsightDiagnostics
    schema_version: str = "1.0.0"
    generator_version: str = "2.2.3"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
