from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class FollowUpExplainability(BaseModel):
    policy_applied: str
    decision_reason: str
    strategy: Optional[str] = None
    strategy_instructions: Optional[str] = None
    factors_considered: dict
    confidence: int

class FollowUpDecision(BaseModel):
    should_follow_up: bool
    reason: str
    priority: str = "normal"
    scheduled_for: Optional[datetime] = None
    risk_score: Optional[int] = None
    explainability: Optional[FollowUpExplainability] = None

class StrategyDecision(BaseModel):
    strategy: str
    instructions: str

class QualityCheckResult(BaseModel):
    passed: bool
    issues: List[str]

class GeneratedMessage(BaseModel):
    content: str
    confidence: int

class UpdateMessageRequest(BaseModel):
    message: str

class RescheduleRequest(BaseModel):
    scheduled_for: datetime

class AssignRequest(BaseModel):
    user_id: UUID

class CancelRequest(BaseModel):
    reason: str

class FollowUpQueueSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    customer_id: UUID
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    status: str
    reason: str
    strategy: Optional[str] = None
    priority: str
    scheduled_for: datetime
    human_paused: bool
    retry_count: int

class FollowUpQueueDetail(FollowUpQueueSummary):
    generated_message: Optional[str]
    final_message: Optional[str]
    channel: str
    explainability_report: Optional[dict]
    confidence_score: Optional[int]
    risk_score: Optional[int]
    cancellation_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    executed_at: Optional[datetime]
    executions: List[dict] = []

class FollowUpQueuePage(BaseModel):
    items: List[FollowUpQueueSummary]
    total: int
    page: int
    page_size: int
    has_next: bool

class FollowUpOverviewStats(BaseModel):
    pending_followups: int
    due_today: int
    sent_today: int
    failed_today: int
    paused_needs_review: int
    strategy_distribution: dict

class LeadHealthSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    score: int
    band: str
    reasons: List[str]
    positive_signals: List[str]
    recommendation: Optional[str]

class SalesTimelineEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_type: str
    title: str
    description: Optional[str]
    created_at: datetime
