"""
HunterOS Engage V1 - Conversation Insight REST Schemas
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

Pydantic v2 schemas for API requests and responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BuildInsightsRequest(BaseModel):
    """Payload to trigger insight generation for a conversation."""
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    scope_type: str = "CONVERSATION"


class InsightEvidenceResponse(BaseModel):
    source_message_ids: List[str] = Field(default_factory=list)
    source_event_ids: List[str] = Field(default_factory=list)
    source_milestone_ids: List[str] = Field(default_factory=list)
    source_moment_ids: List[str] = Field(default_factory=list)
    fact_ids: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    text_snippets: List[str] = Field(default_factory=list)
    extraction_method: str
    confidence: float


class RiskInsightResponse(BaseModel):
    risk_id: str
    category: str
    title: str
    description: str
    impact_description: Optional[str] = None
    priority: str
    confidence: float
    evidence: InsightEvidenceResponse
    created_at: datetime


class OpportunityInsightResponse(BaseModel):
    opportunity_id: str
    category: str
    title: str
    description: str
    value_potential: Optional[str] = None
    qualification_criteria: List[str] = Field(default_factory=list)
    priority: str
    confidence: float
    evidence: InsightEvidenceResponse
    created_at: datetime


class ActionItemInsightResponse(BaseModel):
    action_id: str
    category: str
    owner_type: str
    title: str
    description: str
    due_date_hint: Optional[str] = None
    priority: str
    confidence: float
    evidence: InsightEvidenceResponse
    created_at: datetime


class ConversationInsightResponse(BaseModel):
    insight_id: str
    insight_type: str
    category: str
    title: str
    description: str
    priority: str
    confidence: float
    evidence: InsightEvidenceResponse
    created_at: datetime


class InsightMetadataResponse(BaseModel):
    insight_result_id: str
    conversation_id: str
    workspace_id: Optional[str] = None
    customer_id: Optional[str] = None
    scope_type: str
    total_insights: int
    total_risks: int
    total_opportunities: int
    total_action_items: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    category_distribution: Dict[str, int]
    schema_version: str
    generator_version: str
    generated_at: datetime


class InsightDiagnosticsResponse(BaseModel):
    pipeline_execution_time_ms: float
    stage_timings_ms: Dict[str, float]
    stages_executed: List[str]
    warnings: List[str]
    validation_errors: List[str]
    is_valid: bool


class ConversationInsightResultResponse(BaseModel):
    insight_result_id: str
    conversation_id: str
    workspace_id: Optional[str] = None
    customer_id: Optional[str] = None
    scope_type: str
    metadata: InsightMetadataResponse
    risks: List[RiskInsightResponse]
    opportunities: List[OpportunityInsightResponse]
    action_items: List[ActionItemInsightResponse]
    all_insights: List[ConversationInsightResponse]
    diagnostics: InsightDiagnosticsResponse
    schema_version: str
    generator_version: str
    created_at: datetime
