"""
HunterOS Engage V1 - Intent Intelligence API Schemas (Pydantic v2)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.intents.models import (
    BusinessImportance,
    EvidenceNodeType,
    IntentDetectionMethod,
    IntentTaxonomyCategory,
    IntentType,
)


class EvidenceNodeDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    node_type: EvidenceNodeType
    title: str
    snippet: Optional[str] = None
    confidence: float = 1.0
    occurred_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceEdgeDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_node_id: str
    target_node_id: str
    relation_type: str
    weight: float = 1.0


class IntentEvidenceGraphDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    nodes: List[EvidenceNodeDTO] = Field(default_factory=list)
    edges: List[EvidenceEdgeDTO] = Field(default_factory=list)


class IntentEvidenceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_message_ids: List[str] = Field(default_factory=list)
    source_event_ids: List[uuid.UUID] = Field(default_factory=list)
    source_fact_ids: List[uuid.UUID] = Field(default_factory=list)
    source_milestone_ids: List[uuid.UUID] = Field(default_factory=list)
    source_moment_ids: List[uuid.UUID] = Field(default_factory=list)
    source_insight_ids: List[uuid.UUID] = Field(default_factory=list)
    source_topic_names: List[str] = Field(default_factory=list)
    text_snippets: List[str] = Field(default_factory=list)
    detection_method: IntentDetectionMethod = IntentDetectionMethod.RULE_BASED
    confidence_score: float = 1.0
    evidence_graph: Optional[IntentEvidenceGraphDTO] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentProvenanceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent_version: str = "1.0.0"
    detector_version: str = "1.0.0"
    rule_version: str = "1.0.0"
    rule_pack_name: str = "CoreRulePack"
    rule_name: str = "StandardIntentRule"
    generated_at: datetime


class DetectedIntentDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent_id: uuid.UUID
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    intent_type: IntentType
    taxonomy_category: IntentTaxonomyCategory
    taxonomy_path: str
    business_importance: BusinessImportance
    title: str
    description: str
    confidence: float
    detection_method: IntentDetectionMethod
    supporting_evidence: IntentEvidenceDTO
    provenance: IntentProvenanceDTO
    source_messages: List[str]
    source_events: List[uuid.UUID]
    source_facts: List[uuid.UUID]
    detected_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentMetadataDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    total_intents: int
    primary_intent: Optional[IntentType] = None
    dominant_category: Optional[IntentTaxonomyCategory] = None
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    type_distribution: Dict[str, int] = Field(default_factory=dict)
    average_confidence: float
    generated_at: datetime


class RuleExecutionReportDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    executed_rules: List[str] = Field(default_factory=list)
    matched_rules: List[str] = Field(default_factory=list)
    rejected_rules: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    conflict_count: int = 0
    rule_match_details: Dict[str, Any] = Field(default_factory=dict)


class IntentDiagnosticsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    pipeline_execution_time_ms: float
    stage_timings_ms: Dict[str, float]
    stages_executed: List[str]
    rules_evaluated: int
    intents_detected_raw: int
    intents_deduplicated: int
    rule_report: RuleExecutionReportDTO
    warnings: List[str]
    validation_errors: List[str]
    is_valid: bool


class IntentDetectionResultDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    detection_id: uuid.UUID
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    detected_at: datetime
    schema_version: str = "1.0.0"
    intents: List[DetectedIntentDTO]
    metadata: IntentMetadataDTO
    diagnostics: IntentDiagnosticsDTO
