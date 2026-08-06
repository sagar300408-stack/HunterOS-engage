"""
HunterOS Engage V1 - Intent Classification DTO Schemas
Pydantic schemas for API serialization, requests, responses, and view projections.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassificationMethod,
    IntentCategory,
    IntentGroupType,
    IntentRelationshipType,
)


class IntentRelationshipDTO(BaseModel):
    relationship_id: uuid.UUID
    source_intent_id: uuid.UUID
    target_intent_id: uuid.UUID
    relationship_type: IntentRelationshipType
    reason: str
    confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class IntentGroupDTO(BaseModel):
    group_id: uuid.UUID
    group_type: IntentGroupType
    name: str
    description: str
    intent_ids: List[uuid.UUID]
    primary_intent_id: Optional[uuid.UUID] = None
    aggregate_confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ClassifiedIntentDTO(BaseModel):
    classified_intent_id: uuid.UUID
    original_intent_id: uuid.UUID
    canonical_intent_id: uuid.UUID
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    business_category: IntentCategory
    business_domain: BusinessDomain
    business_process: str
    taxonomy_path: str
    taxonomy_paths: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    confidence: float
    classification_method: ClassificationMethod
    supporting_evidence: Dict[str, Any]
    relationships: List[IntentRelationshipDTO] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    classified_at: datetime


class ClassificationMetadataDTO(BaseModel):
    classification_id: uuid.UUID
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    classification_version: str
    taxonomy_version: str
    total_detected_intents: int
    total_classified_intents: int
    total_relationships: int
    total_groups: int
    primary_category: Optional[IntentCategory] = None
    primary_domain: Optional[BusinessDomain] = None
    primary_process: Optional[str] = None
    category_distribution: Dict[str, int]
    domain_distribution: Dict[str, int]
    group_distribution: Dict[str, int]
    execution_duration_ms: float
    created_at: datetime


class ClassificationDiagnosticsDTO(BaseModel):
    is_valid: bool
    applied_plugins: List[str]
    applied_rule_packs: List[str]
    executed_rules: List[str]
    matched_rules: List[str]
    rejected_rules: List[str]
    validation_warnings: List[str]
    validation_errors: List[str]
    stage_timings_ms: Dict[str, float]


class ClassificationProvenanceDTO(BaseModel):
    classification_version: str
    taxonomy_version: str
    detection_result_id: Optional[uuid.UUID] = None
    rule_packs: List[str]
    plugin_versions: Dict[str, str]
    source_event_count: int
    source_fact_count: int
    source_insight_count: int
    classified_by: str
    generated_at: datetime


class IntentClassificationResultDTO(BaseModel):
    classification_id: uuid.UUID
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    classified_intents: List[ClassifiedIntentDTO]
    relationships: List[IntentRelationshipDTO]
    groups: List[IntentGroupDTO]
    metadata: ClassificationMetadataDTO
    diagnostics: ClassificationDiagnosticsDTO
    provenance: ClassificationProvenanceDTO


class ClassifyIntentsRequest(BaseModel):
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    force_reclassification: bool = False
    active_plugins: Optional[List[str]] = None


class IntentAnalyticsQueryDTO(BaseModel):
    workspace_id: Optional[uuid.UUID] = None
    total_classifications: int
    total_classified_intents: int
    category_distribution: Dict[str, int]
    domain_distribution: Dict[str, int]
    process_distribution: Dict[str, int]
    relationship_distribution: Dict[str, int]
    group_distribution: Dict[str, int]
    coverage_rate: float
    average_confidence: float
    rule_usage_counts: Dict[str, int]
