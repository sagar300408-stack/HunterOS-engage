"""
HunterOS Engage V1 - Intent Intelligence Domain Models
Phase 2.3.1: Intent Intelligence – Intent Detection

Architectural Invariants:
1. Strict descriptive customer objective identification only.
2. No Memory updates, no direct Memory queries.
3. No customer journey updates, no recommendations, no lead scoring, no sentiment analysis.
4. Full evidence graph traceability (Messages, Facts, Timeline Events, Milestones, Moments, Insights).
5. Comprehensive provenance and rule execution diagnostics.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


# ── 1. Taxonomy & Classification Enums ─────────────────────────────────────────

class IntentTaxonomyCategory(str, enum.Enum):
    """Hierarchical category grouping for high-level business routing and analytics."""
    COMMERCIAL = "Commercial"
    OPERATIONAL = "Operational"
    OPERATIONS = "Operational"
    RELATIONSHIP = "Relationship"
    INFORMATION = "Information"
    CUSTOM = "Custom"
    SUPPORT = "Operational"


class IntentType(str, enum.Enum):
    """The 20 standard deterministic business intent types."""
    # Commercial
    PROPERTY_INQUIRY = "PROPERTY_INQUIRY"
    PRODUCT_INQUIRY = "PRODUCT_INQUIRY"
    PRICING_INQUIRY = "PRICING_INQUIRY"
    BUDGET_DISCUSSION = "BUDGET_DISCUSSION"
    BOOKING_INTEREST = "BOOKING_INTEREST"
    NEGOTIATION = "NEGOTIATION"
    FINANCE_INQUIRY = "FINANCE_INQUIRY"
    INVESTMENT_INQUIRY = "INVESTMENT_INQUIRY"
    COMMERCIAL_INQUIRY = "PRODUCT_INQUIRY"
    PURCHASE_INTENT = "PRODUCT_INQUIRY"

    # Operational
    DOCUMENT_REQUEST = "DOCUMENT_REQUEST"
    REQUEST_DOCUMENT = "DOCUMENT_REQUEST"
    SUPPORT_REQUEST = "SUPPORT_REQUEST"
    SCHEDULE_MEETING = "SCHEDULE_MEETING"
    SCHEDULE_SITE_VISIT = "SCHEDULE_SITE_VISIT"
    PROPOSAL_REQUEST = "PROPOSAL_REQUEST"
    CANCELLATION = "CANCELLATION"
    CANCEL_SERVICE = "CANCELLATION"

    # Relationship
    REFERRAL = "REFERRAL"
    PARTNERSHIP_INQUIRY = "PARTNERSHIP_INQUIRY"
    COMPLAINT = "COMPLAINT"

    # Information
    INFORMATION_REQUEST = "INFORMATION_REQUEST"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"

    # Custom
    CUSTOM_INTENT = "CUSTOM_INTENT"


class BusinessImportance(str, enum.Enum):
    """
    Descriptive business importance of the detected intent.
    NOTE: Descriptive only — NOT prescriptive priority (which belongs to Recommendation Intelligence).
    """
    INFORMATIONAL = "INFORMATIONAL"
    OPERATIONAL = "OPERATIONAL"
    COMMERCIAL = "COMMERCIAL"
    CRITICAL_COMMUNICATION = "CRITICAL_COMMUNICATION"
    HIGH = "COMMERCIAL"
    CRITICAL = "CRITICAL_COMMUNICATION"
    MEDIUM = "OPERATIONAL"
    LOW = "INFORMATIONAL"


class IntentDetectionMethod(str, enum.Enum):
    """Method used by detector to identify candidate intents."""
    RULE_BASED = "RULE_BASED"
    FACT_MATCHING = "FACT_MATCHING"
    KEYWORD_MATCHING = "KEYWORD_MATCHING"
    EVENT_MAPPING = "EVENT_MAPPING"
    MOMENT_MAPPING = "MOMENT_MAPPING"
    INSIGHT_DERIVED = "INSIGHT_DERIVED"
    CUSTOM = "CUSTOM"


# ── 2. Evidence Graph Models ──────────────────────────────────────────────────

class EvidenceNodeType(str, enum.Enum):
    """Types of artifact nodes in the traceability evidence graph."""
    MESSAGE = "MESSAGE"
    FACT = "FACT"
    TIMELINE_EVENT = "TIMELINE_EVENT"
    TIMELINE_MILESTONE = "TIMELINE_MILESTONE"
    IMPORTANT_MOMENT = "IMPORTANT_MOMENT"
    INSIGHT = "INSIGHT"
    TOPIC = "TOPIC"


@dataclass(frozen=True)
class EvidenceNode:
    """A node in the explainable evidence graph representing an observed artifact."""
    node_id: str
    node_type: EvidenceNodeType
    title: str
    snippet: Optional[str] = None
    confidence: float = 1.0
    occurred_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "title": self.title,
            "snippet": self.snippet,
            "confidence": self.confidence,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class EvidenceEdge:
    """Directed relationship between evidence nodes or from intent to evidence node."""
    source_node_id: str
    target_node_id: str
    relation_type: str  # e.g., 'TRIGGERED_BY', 'CORROBORATED_BY', 'DERIVED_FROM'
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relation_type": self.relation_type,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class IntentEvidenceGraph:
    """Complete explainability and lineage graph for a detected intent."""
    nodes: List[EvidenceNode] = field(default_factory=list)
    edges: List[EvidenceEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }


@dataclass(frozen=True)
class IntentEvidence:
    """Comprehensive supporting evidence linking intent back to observed artifacts."""
    source_message_ids: List[str] = field(default_factory=list)
    source_event_ids: List[uuid.UUID] = field(default_factory=list)
    source_fact_ids: List[uuid.UUID] = field(default_factory=list)
    source_milestone_ids: List[uuid.UUID] = field(default_factory=list)
    source_moment_ids: List[uuid.UUID] = field(default_factory=list)
    source_insight_ids: List[uuid.UUID] = field(default_factory=list)
    source_topic_names: List[str] = field(default_factory=list)
    text_snippets: List[str] = field(default_factory=list)
    detection_method: IntentDetectionMethod = IntentDetectionMethod.RULE_BASED
    confidence_score: float = 1.0
    evidence_graph: Optional[IntentEvidenceGraph] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_sufficient_evidence(self) -> bool:
        return bool(
            self.source_message_ids
            or self.source_event_ids
            or self.source_fact_ids
            or self.source_milestone_ids
            or self.source_moment_ids
            or self.source_insight_ids
            or self.source_topic_names
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_message_ids": list(self.source_message_ids),
            "source_event_ids": [str(eid) for eid in self.source_event_ids],
            "source_fact_ids": [str(fid) for fid in self.source_fact_ids],
            "source_milestone_ids": [str(mid) for mid in self.source_milestone_ids],
            "source_moment_ids": [str(mid) for mid in self.source_moment_ids],
            "source_insight_ids": [str(iid) for iid in self.source_insight_ids],
            "source_topic_names": list(self.source_topic_names),
            "text_snippets": list(self.text_snippets),
            "detection_method": self.detection_method.value,
            "confidence_score": self.confidence_score,
            "evidence_graph": self.evidence_graph.to_dict() if self.evidence_graph else None,
            "metadata": dict(self.metadata),
        }


# ── 3. Provenance & Version Tracking ──────────────────────────────────────────

@dataclass(frozen=True)
class IntentProvenance:
    """Exact audit provenance for a detected intent."""
    intent_version: str = "1.0.0"
    detector_version: str = "1.0.0"
    rule_version: str = "1.0.0"
    rule_pack_name: str = "CoreRulePack"
    rule_name: str = "StandardIntentRule"
    detection_engine_version: str = "1.0.0"
    total_messages_analyzed: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_version": self.intent_version,
            "detector_version": self.detector_version,
            "rule_version": self.rule_version,
            "rule_pack_name": self.rule_pack_name,
            "rule_name": self.rule_name,
            "detection_engine_version": self.detection_engine_version,
            "total_messages_analyzed": self.total_messages_analyzed,
            "generated_at": self.generated_at.isoformat(),
        }


# ── 4. Domain Entities ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DetectedIntent:
    """
    Immutable detected business intent entity.
    Represents what the customer explicitly seeks to accomplish.
    """
    intent_id: uuid.UUID = field(default_factory=uuid.uuid4)
    conversation_id: str = ""
    workspace_id: Optional[Any] = None
    customer_id: Optional[str] = None
    intent_type: Any = IntentType.GENERAL_INQUIRY
    taxonomy_category: Any = IntentTaxonomyCategory.INFORMATION
    taxonomy_path: str = "information/general_inquiry"
    business_importance: Any = BusinessImportance.INFORMATIONAL
    title: str = ""
    description: str = ""
    confidence: float = 1.0
    detection_method: Any = IntentDetectionMethod.RULE_BASED
    supporting_evidence: IntentEvidence = field(default_factory=IntentEvidence)
    provenance: IntentProvenance = field(default_factory=IntentProvenance)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    category: Any = None
    confidence_score: Any = None
    supporting_evidence_message_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.category is not None:
            object.__setattr__(self, "taxonomy_category", self.category)
        if self.confidence_score is not None:
            object.__setattr__(self, "confidence", float(self.confidence_score))
        if self.supporting_evidence_message_ids and not self.supporting_evidence.source_message_ids:
            object.__setattr__(
                self,
                "supporting_evidence",
                IntentEvidence(source_message_ids=list(self.supporting_evidence_message_ids)),
            )

    @property
    def source_messages(self) -> List[str]:
        return list(self.supporting_evidence.source_message_ids)

    @property
    def source_events(self) -> List[uuid.UUID]:
        return list(self.supporting_evidence.source_event_ids)

    @property
    def source_facts(self) -> List[uuid.UUID]:
        return list(self.supporting_evidence.source_fact_ids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": str(self.intent_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "intent_type": self.intent_type.value if hasattr(self.intent_type, "value") else str(self.intent_type),
            "taxonomy_category": self.taxonomy_category.value if hasattr(self.taxonomy_category, "value") else str(self.taxonomy_category),
            "taxonomy_path": self.taxonomy_path,
            "business_importance": self.business_importance.value if hasattr(self.business_importance, "value") else str(self.business_importance),
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "detection_method": self.detection_method.value if hasattr(self.detection_method, "value") else str(self.detection_method),
            "supporting_evidence": self.supporting_evidence.to_dict(),
            "provenance": self.provenance.to_dict(),
            "source_messages": self.source_messages,
            "source_events": [str(eid) for eid in self.source_events],
            "source_facts": [str(fid) for fid in self.source_facts],
            "detected_at": self.detected_at.isoformat(),
            "metadata": dict(self.metadata),
        }


# ── 5. Metadata, Diagnostics & Aggregate Root ─────────────────────────────────

@dataclass(frozen=True)
class IntentMetadata:
    """Summary statistics for detected intents."""
    conversation_id: str = ""
    workspace_id: Optional[Any] = None
    customer_id: Optional[str] = None
    total_intents: int = 0
    primary_intent: Optional[Any] = None
    dominant_category: Optional[Any] = None
    category_distribution: Dict[str, int] = field(default_factory=dict)
    type_distribution: Dict[str, int] = field(default_factory=dict)
    average_confidence: float = 0.0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "total_intents": self.total_intents,
            "primary_intent": self.primary_intent.value if hasattr(self.primary_intent, "value") else (str(self.primary_intent) if self.primary_intent else None),
            "dominant_category": self.dominant_category.value if hasattr(self.dominant_category, "value") else (str(self.dominant_category) if self.dominant_category else None),
            "category_distribution": dict(self.category_distribution),
            "type_distribution": dict(self.type_distribution),
            "average_confidence": self.average_confidence,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass(frozen=True)
class RuleExecutionReport:
    """Detailed telemetry and audit metrics on rule pack execution."""
    executed_rules: List[str] = field(default_factory=list)
    matched_rules: List[str] = field(default_factory=list)
    rejected_rules: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    conflict_count: int = 0
    rule_match_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executed_rules": list(self.executed_rules),
            "matched_rules": list(self.matched_rules),
            "rejected_rules": list(self.rejected_rules),
            "execution_time_ms": self.execution_time_ms,
            "conflict_count": self.conflict_count,
            "rule_match_details": dict(self.rule_match_details),
        }


@dataclass(frozen=True)
class IntentDiagnostics:
    """Operational timing, invariant checks, and rule execution diagnostics."""
    pipeline_execution_time_ms: float = 0.0
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    stages_executed: List[str] = field(default_factory=list)
    rules_evaluated: int = 0
    intents_detected_raw: int = 0
    intents_deduplicated: int = 0
    rule_report: RuleExecutionReport = field(default_factory=RuleExecutionReport)
    warnings: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    is_valid: bool = True
    rules_executed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_execution_time_ms": self.pipeline_execution_time_ms,
            "stage_timings_ms": dict(self.stage_timings_ms),
            "stages_executed": list(self.stages_executed),
            "rules_evaluated": self.rules_evaluated,
            "intents_detected_raw": self.intents_detected_raw,
            "intents_deduplicated": self.intents_deduplicated,
            "rule_report": self.rule_report.to_dict(),
            "warnings": list(self.warnings),
            "validation_errors": list(self.validation_errors),
            "is_valid": self.is_valid,
        }


@dataclass(frozen=True)
class IntentDetectionResult:
    """
    Immutable aggregate root emitted by the Intent Detection Engine.
    This is the official artifact consumed by downstream intelligence modules.
    """
    detection_id: uuid.UUID = field(default_factory=uuid.uuid4)
    conversation_id: str = ""
    workspace_id: Optional[Any] = None
    customer_id: Optional[str] = None
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"

    intents: List[DetectedIntent] = field(default_factory=list)
    detected_intents: List[DetectedIntent] = field(default_factory=list)
    metadata: Any = field(
        default_factory=lambda: IntentMetadata(conversation_id="")
    )
    diagnostics: Any = field(default_factory=IntentDiagnostics)
    provenance: Any = field(default_factory=IntentProvenance)

    def __post_init__(self) -> None:
        if self.detected_intents and not self.intents:
            object.__setattr__(self, "intents", list(self.detected_intents))
        elif self.intents and not self.detected_intents:
            object.__setattr__(self, "detected_intents", list(self.intents))

    def get_intents_by_type(self, intent_type: IntentType) -> List[DetectedIntent]:
        return [i for i in self.intents if i.intent_type == intent_type]

    def get_intents_by_category(
        self, category: IntentTaxonomyCategory
    ) -> List[DetectedIntent]:
        return [i for i in self.intents if i.taxonomy_category == category]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": str(self.detection_id),
            "conversation_id": self.conversation_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "customer_id": self.customer_id,
            "detected_at": self.detected_at.isoformat(),
            "schema_version": self.schema_version,
            "intents": [i.to_dict() for i in self.intents],
            "detected_intents": [i.to_dict() for i in self.detected_intents],
            "metadata": self.metadata.to_dict() if hasattr(self.metadata, "to_dict") else self.metadata,
            "diagnostics": self.diagnostics.to_dict() if hasattr(self.diagnostics, "to_dict") else self.diagnostics,
            "provenance": self.provenance.to_dict() if hasattr(self.provenance, "to_dict") else self.provenance,
        }


# Aliases for cross-subsystem consistency
IntentDetectionDiagnostics = IntentDiagnostics
IntentDetectionProvenance = IntentProvenance
