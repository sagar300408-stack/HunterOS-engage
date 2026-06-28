"""
Dashboard domain Pydantic schemas.

All API response models for the dashboard endpoints.
Grouped by feature area for clarity.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: Optional[str] = None
    workspace_id: str


class UserSchema(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    role: str
    workspace_id: UUID
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Overview metrics ──────────────────────────────────────────────────────────

class MetricCard(BaseModel):
    label: str
    value: int | float
    unit: Optional[str] = None       # e.g. "ms", "%", "$"
    trend: Optional[float] = None    # percentage change vs previous period
    trend_direction: Optional[str] = None  # "up" | "down" | "neutral"


class OverviewMetrics(BaseModel):
    active_conversations: MetricCard
    total_customers: MetricCard
    new_leads_today: MetricCard
    qualified_leads: MetricCard
    purchase_ready: MetricCard
    avg_response_time_ms: MetricCard
    ai_success_rate: MetricCard
    memory_updates_today: MetricCard
    total_cost_today_usd: MetricCard


# ── Conversations ─────────────────────────────────────────────────────────────

class ConversationSummary(BaseModel):
    id: UUID
    customer_id: Optional[UUID]
    customer_name: Optional[str]
    customer_phone: str
    last_message: Optional[str]
    last_message_direction: Optional[str]
    last_activity: Optional[datetime]
    message_count: int
    detected_intent: Optional[str]
    buying_stage: Optional[str]
    urgency: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationPage(BaseModel):
    items: list[ConversationSummary]
    total: int
    page: int
    page_size: int
    has_next: bool


class IntentSummary(BaseModel):
    detected_intent: str
    confidence: float
    urgency: str
    buying_stage: Optional[str]
    budget: Optional[str]
    budget_confidence: Optional[float]
    timeline: Optional[str]
    interest: Optional[str]
    location: Optional[str]
    next_action: Optional[str]
    reasoning: Optional[str]
    memory_influenced: Optional[str]
    detected_keywords: Optional[list[str]]
    created_at: datetime


class MessageDetail(BaseModel):
    id: UUID
    direction: str
    content: str
    timestamp: datetime
    intent: Optional[IntentSummary] = None
    ai_model: Optional[str] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class ConversationDetail(BaseModel):
    id: UUID
    customer_id: Optional[UUID]
    customer_name: Optional[str]
    customer_phone: str
    created_at: datetime
    messages: list[MessageDetail]
    pipeline_events: list["PipelineEventSchema"]


# ── Customers ─────────────────────────────────────────────────────────────────

class CustomerSummary(BaseModel):
    id: UUID
    name: Optional[str]
    phone: str
    email: Optional[str]
    status: str
    buying_stage: Optional[str]
    qualification_score: Optional[int]
    qualification_grade: Optional[str]
    last_interaction: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerPage(BaseModel):
    items: list[CustomerSummary]
    total: int
    page: int
    page_size: int
    has_next: bool


class MemorySummary(BaseModel):
    summary: Optional[str]
    budget: Optional[dict]
    timeline: Optional[dict]
    preferred_location: Optional[dict]
    interests: Optional[list]
    message_count: int
    last_updated: Optional[datetime]


class CustomerProfile(BaseModel):
    id: UUID
    name: Optional[str]
    phone: str
    email: Optional[str]
    status: str
    buying_stage: Optional[str]
    notes: Optional[str]
    preferred_language: str
    created_at: datetime
    last_interaction: Optional[datetime]
    memory: Optional[MemorySummary]
    recent_intents: list[IntentSummary]
    conversation_count: int
    qualification: Optional[dict]


class UpdateCustomerRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ── Leads ─────────────────────────────────────────────────────────────────────

class LeadCard(BaseModel):
    customer_id: UUID
    name: Optional[str]
    phone: str
    buying_stage: str
    urgency: Optional[str]
    budget: Optional[str]
    timeline: Optional[str]
    interest: Optional[str]
    qualification_score: int
    qualification_grade: str
    last_interaction: Optional[datetime]


class LeadPipeline(BaseModel):
    stages: dict[str, list[LeadCard]]
    # Keys: "Research", "Comparing Options", "Ready to Schedule", "Negotiation", "Purchase Ready"


class UpdateLeadStageRequest(BaseModel):
    buying_stage: str
    reason: Optional[str] = None   # logged in audit_log


# ── Analytics ─────────────────────────────────────────────────────────────────

class DailyMetric(BaseModel):
    date: str             # "YYYY-MM-DD"
    value: int | float


class IntentDistribution(BaseModel):
    intent: str
    count: int
    percentage: float


class CostMetrics(BaseModel):
    total_cost_usd: float
    avg_cost_per_conversation: float
    avg_cost_per_lead: float
    avg_cost_per_qualified_lead: float
    total_prompt_tokens: int
    total_completion_tokens: int
    avg_tokens_per_response: float


class AnalyticsData(BaseModel):
    date_from: str
    date_to: str
    conversations_per_day: list[DailyMetric]
    leads_per_day: list[DailyMetric]
    intent_distribution: list[IntentDistribution]
    avg_response_time_per_day: list[DailyMetric]
    cost_metrics: CostMetrics


# ── System Health ─────────────────────────────────────────────────────────────

class ServiceStatus(BaseModel):
    name: str
    status: str          # "online" | "warning" | "offline" | "not_configured"
    latency_ms: Optional[int] = None
    uptime_pct: Optional[float] = None
    detail: Optional[str] = None


class SystemHealth(BaseModel):
    overall: str         # "healthy" | "degraded" | "down"
    services: list[ServiceStatus]
    checked_at: datetime


# ── Activity Feed ─────────────────────────────────────────────────────────────

class ActivityEvent(BaseModel):
    id: UUID
    event_type: str
    description: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    metadata: Optional[dict]
    created_at: datetime


# ── Pipeline Replay ───────────────────────────────────────────────────────────

class PipelineEventSchema(BaseModel):
    id: UUID
    step: str
    status: str
    duration_ms: Optional[int]
    payload: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Queue Monitor ─────────────────────────────────────────────────────────────

class BackgroundJobSchema(BaseModel):
    id: UUID
    job_type: str
    status: str
    run_count: int
    last_error: Optional[str]
    scheduled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class QueueStatus(BaseModel):
    pending: int
    running: int
    completed_today: int
    failed: int
    jobs: list[BackgroundJobSchema]


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLogSchema(BaseModel):
    id: UUID
    action: str
    target_type: str
    target_id: Optional[UUID]
    user_email: Optional[str]
    payload: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Search ────────────────────────────────────────────────────────────────────

class SearchHit(BaseModel):
    type: str            # "customer" | "conversation" | "memory" | "intent"
    id: UUID
    title: str
    subtitle: Optional[str]
    highlight: Optional[str]  # matched snippet
    score: float


class SearchResults(BaseModel):
    query: str
    total: int
    hits: list[SearchHit]


# ── WebSocket events ──────────────────────────────────────────────────────────

class WSEvent(BaseModel):
    event: str
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
