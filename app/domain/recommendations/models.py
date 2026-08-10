from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class RecommendationType(str, Enum):
    FOLLOW_UP = "FOLLOW_UP"
    CONTACT_CUSTOMER = "CONTACT_CUSTOMER"
    SCHEDULE_MEETING = "SCHEDULE_MEETING"
    SCHEDULE_SITE_VISIT = "SCHEDULE_SITE_VISIT"
    SEND_DOCUMENT = "SEND_DOCUMENT"
    SEND_INFORMATION = "SEND_INFORMATION"
    DISCUSS_PRICING = "DISCUSS_PRICING"
    DISCUSS_FINANCING = "DISCUSS_FINANCING"
    PROPERTY_ALTERNATIVE = "PROPERTY_ALTERNATIVE"
    PRODUCT_ALTERNATIVE = "PRODUCT_ALTERNATIVE"
    RESOLVE_REQUEST = "RESOLVE_REQUEST"
    ESCALATE = "ESCALATE"
    REVIEW_CUSTOMER = "REVIEW_CUSTOMER"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    CUSTOM = "CUSTOM"

class RecommendationStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISMISSED = "DISMISSED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"

class RecommendationSource(str, Enum):
    RULE = "RULE"
    SYSTEM = "SYSTEM"
    MODULE = "MODULE"
    USER = "USER"
    EXTERNAL = "EXTERNAL"
    CUSTOM = "CUSTOM"

class RecommendationScope(str, Enum):
    CUSTOMER = "CUSTOMER"
    CONVERSATION = "CONVERSATION"
    INTENT = "INTENT"
    JOURNEY = "JOURNEY"
    OPPORTUNITY = "OPPORTUNITY"
    PROPERTY = "PROPERTY"
    WORKSPACE = "WORKSPACE"
    CUSTOM = "CUSTOM"

class RecommendationPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNASSIGNED = "UNASSIGNED"

@dataclass(frozen=True)
class RecommendationConfidence:
    value: float
    
    def __post_init__(self):
        if not (0.0 <= self.value <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")

@dataclass(frozen=True)
class RecommendationActorContext:
    actor_id: str
    actor_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class RecommendationTarget:
    target_id: str
    target_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Recommendation:
    id: UUID
    workspace_id: UUID
    type: RecommendationType
    status: RecommendationStatus
    source: RecommendationSource
    scope: RecommendationScope
    priority: RecommendationPriority
    confidence: RecommendationConfidence
    title: str
    description: str
    action_url: Optional[str] = None
    actor_context: Optional[RecommendationActorContext] = None
    targets: List[RecommendationTarget] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

@dataclass(frozen=True)
class RecommendationDetectionResult:
    workspace_id: str
    target_id: Optional[str]
    candidates: List[Any] = field(default_factory=list)

