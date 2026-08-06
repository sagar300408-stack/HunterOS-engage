"""
HunterOS Engage V1 - Intent Classification Domain Models
Core entities and enums for structured business intent classification.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.domain.intents.models import IntentEvidence


# ── Enumerations ─────────────────────────────────────────────────────────────

class IntentCategory(str, Enum):
    """High-level business categorization of intents."""
    COMMERCIAL = "COMMERCIAL"
    OPERATIONAL = "OPERATIONAL"
    RELATIONSHIP = "RELATIONSHIP"
    INFORMATION = "INFORMATION"
    CUSTOM = "CUSTOM"


class BusinessDomain(str, Enum):
    """Vertical industry or operational domain."""
    REAL_ESTATE = "REAL_ESTATE"
    HEALTHCARE = "HEALTHCARE"
    MANUFACTURING = "MANUFACTURING"
    FINANCIAL_SERVICES = "FINANCIAL_SERVICES"
    SAAS = "SAAS"
    ECOMMERCE = "ECOMMERCE"
    CROSS_INDUSTRY = "CROSS_INDUSTRY"
    TECHNOLOGY = "TECHNOLOGY"
    CUSTOM = "CUSTOM"


class ClassificationMethod(str, Enum):
    """Method used to classify the intent."""
    RULE_BASED = "RULE_BASED"
    DETERMINISTIC_RULE = "DETERMINISTIC_RULE"
    TAXONOMY_GRAPH_MAPPING = "TAXONOMY_GRAPH_MAPPING"
    CONTEXTUAL_ENRICHMENT = "CONTEXTUAL_ENRICHMENT"
    RELATIONSHIP_INFERENCE = "RELATIONSHIP_INFERENCE"
    INDUSTRY_PLUGIN = "INDUSTRY_PLUGIN"
    HYBRID_CLASSIFICATION = "HYBRID_CLASSIFICATION"


class IntentRelationshipType(str, Enum):
    """Descriptive structural or contextual relationship between intents."""
    PARENT_INTENT = "PARENT_INTENT"
    CHILD_INTENT = "CHILD_INTENT"
    RELATED_INTENT = "RELATED_INTENT"
    DEPENDENT_INTENT = "DEPENDENT_INTENT"
    COMPLEMENTARY_INTENT = "COMPLEMENTARY_INTENT"
    CONFLICTING_INTENT = "CONFLICTING_INTENT"


class IntentGroupType(str, Enum):
    """Functional clustering category for grouped intents."""
    CATEGORY_CLUSTER = "CATEGORY_CLUSTER"
    COMMERCIAL = "COMMERCIAL"
    OPERATIONAL = "OPERATIONAL"
    INFORMATION = "INFORMATION"
    RELATIONSHIP = "RELATIONSHIP"
    CUSTOM = "CUSTOM"


# ── Core Classification Entities ─────────────────────────────────────────────

class IntentRelationship(BaseModel):
    """
    Descriptive relationship link between two intent nodes.
    Zero side-effects or autonomous mutations.
    """
    model_config = ConfigDict(frozen=True)

    relationship_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_intent_id: uuid.UUID
    target_intent_id: uuid.UUID
    relationship_type: IntentRelationshipType
    reason: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": str(self.relationship_id),
            "source_intent_id": str(self.source_intent_id),
            "target_intent_id": str(self.target_intent_id),
            "relationship_type": self.relationship_type.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class IntentGroup(BaseModel):
    """
    Aggregated cluster of related classified intents.
    """
    model_config = ConfigDict(frozen=True)

    group_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    group_type: IntentGroupType
    name: str
    description: str = ""
    intent_ids: List[uuid.UUID] = Field(default_factory=list)
    primary_intent_id: Optional[uuid.UUID] = None
    aggregate_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": str(self.group_id),
            "group_type": self.group_type.value,
            "name": self.name,
            "description": self.description,
            "intent_ids": [str(i) for i in self.intent_ids],
            "primary_intent_id": str(self.primary_intent_id) if self.primary_intent_id else None,
            "aggregate_confidence": self.aggregate_confidence,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class ClassifiedIntent(BaseModel):
    """
    Normalized, enriched business intent model.
    The primary artifact consumed by downstream intelligence modules.
    """
    model_config = ConfigDict(frozen=True)

    classified_intent_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    original_intent_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    canonical_intent_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    business_category: IntentCategory
    business_domain: BusinessDomain
    business_process: str
    taxonomy_path: str
    taxonomy_paths: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    classification_method: ClassificationMethod
    supporting_evidence: IntentEvidence
    relationships: List[IntentRelationship] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    classified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classified_intent_id": str(self.classified_intent_id),
            "original_intent_id": str(self.original_intent_id),
            "canonical_intent_id": str(self.canonical_intent_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "business_category": self.business_category.value,
            "business_domain": self.business_domain.value,
            "business_process": self.business_process,
            "taxonomy_path": self.taxonomy_path,
            "taxonomy_paths": self.taxonomy_paths,
            "aliases": self.aliases,
            "confidence": self.confidence,
            "classification_method": self.classification_method.value,
            "supporting_evidence": self.supporting_evidence.to_dict(),
            "relationships": [r.to_dict() for r in self.relationships],
            "metadata": self.metadata,
            "classified_at": self.classified_at.isoformat(),
        }


# ── Metadata & Diagnostics ───────────────────────────────────────────────────

class ClassificationMetadata(BaseModel):
    """Execution and summary metadata for Intent Classification."""
    model_config = ConfigDict(frozen=True)

    classification_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    classification_version: str = "2.3.2"
    taxonomy_version: str = "2.3.2"
    total_detected_intents: int = 0
    total_classified_intents: int = 0
    total_relationships: int = 0
    total_groups: int = 0
    primary_category: Optional[IntentCategory] = None
    primary_domain: Optional[BusinessDomain] = None
    primary_process: Optional[str] = None
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    domain_distribution: Dict[str, int] = Field(default_factory=dict)
    group_distribution: Dict[str, int] = Field(default_factory=dict)
    execution_duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classification_id": str(self.classification_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "classification_version": self.classification_version,
            "taxonomy_version": self.taxonomy_version,
            "total_detected_intents": self.total_detected_intents,
            "total_classified_intents": self.total_classified_intents,
            "total_relationships": self.total_relationships,
            "total_groups": self.total_groups,
            "primary_category": self.primary_category.value if self.primary_category else None,
            "primary_domain": self.primary_domain.value if self.primary_domain else None,
            "primary_process": self.primary_process,
            "category_distribution": self.category_distribution,
            "domain_distribution": self.domain_distribution,
            "group_distribution": self.group_distribution,
            "execution_duration_ms": self.execution_duration_ms,
            "created_at": self.created_at.isoformat(),
        }


class ClassificationDiagnostics(BaseModel):
    """Execution diagnostics, rules trace, and verification status."""
    model_config = ConfigDict(frozen=True)

    is_valid: bool = True
    applied_plugins: List[str] = Field(default_factory=list)
    applied_rule_packs: List[str] = Field(default_factory=list)
    executed_rules: List[str] = Field(default_factory=list)
    matched_rules: List[str] = Field(default_factory=list)
    rejected_rules: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    stage_timings_ms: Dict[str, float] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "applied_plugins": self.applied_plugins,
            "applied_rule_packs": self.applied_rule_packs,
            "executed_rules": self.executed_rules,
            "matched_rules": self.matched_rules,
            "rejected_rules": self.rejected_rules,
            "validation_warnings": self.validation_warnings,
            "validation_errors": self.validation_errors,
            "stage_timings_ms": self.stage_timings_ms,
        }


class ClassificationProvenance(BaseModel):
    """Complete provenance trace of classification generation."""
    model_config = ConfigDict(frozen=True)

    classification_version: str = "2.3.2"
    taxonomy_version: str = "2.3.2"
    detection_result_id: Optional[uuid.UUID] = None
    rule_packs: List[str] = Field(default_factory=list)
    plugin_versions: Dict[str, str] = Field(default_factory=dict)
    source_event_count: int = 0
    source_fact_count: int = 0
    source_insight_count: int = 0
    classified_by: str = "IntentClassificationEngine_v2.3.2"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classification_version": self.classification_version,
            "taxonomy_version": self.taxonomy_version,
            "detection_result_id": str(self.detection_result_id) if self.detection_result_id else None,
            "rule_packs": self.rule_packs,
            "plugin_versions": self.plugin_versions,
            "source_event_count": self.source_event_count,
            "source_fact_count": self.source_fact_count,
            "source_insight_count": self.source_insight_count,
            "classified_by": self.classified_by,
            "generated_at": self.generated_at.isoformat(),
        }


# ── Aggregate Root ───────────────────────────────────────────────────────────

class IntentClassificationResult(BaseModel):
    """
    Immutable root entity containing the complete classification output for a conversation.
    """
    model_config = ConfigDict(frozen=True)

    classification_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: str
    workspace_id: Optional[uuid.UUID] = None
    customer_id: Optional[str] = None
    classified_intents: List[ClassifiedIntent] = Field(default_factory=list)
    relationships: List[IntentRelationship] = Field(default_factory=list)
    groups: List[IntentGroup] = Field(default_factory=list)
    metadata: ClassificationMetadata
    diagnostics: ClassificationDiagnostics
    provenance: ClassificationProvenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classification_id": str(self.classification_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "classified_intents": [ci.to_dict() for ci in self.classified_intents],
            "relationships": [r.to_dict() for r in self.relationships],
            "groups": [g.to_dict() for g in self.groups],
            "metadata": self.metadata.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "provenance": self.provenance.to_dict(),
        }
