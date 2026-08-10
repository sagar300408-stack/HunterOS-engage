from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

class PriorityLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class UrgencyLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    IMMEDIATE = "IMMEDIATE"

class ImpactLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    TRANSFORMATIONAL = "TRANSFORMATIONAL"

class EvidenceStrength(Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    IRREFUTABLE = "IRREFUTABLE"

class FreshnessLevel(Enum):
    STALE = "STALE"
    RECENT = "RECENT"
    LIVE = "LIVE"

class BlockingLevel(Enum):
    NONE = "NONE"
    PARTIAL = "PARTIAL"
    TOTAL = "TOTAL"

class PriorityFactorType(Enum):
    BUSINESS_VALUE = "BUSINESS_VALUE"
    TIME_SENSITIVITY = "TIME_SENSITIVITY"
    RISK_MITIGATION = "RISK_MITIGATION"
    STRATEGIC_ALIGNMENT = "STRATEGIC_ALIGNMENT"
    USER_IMPACT = "USER_IMPACT"

class PrioritizationMethod(Enum):
    WEIGHTED_SCORING = "WEIGHTED_SCORING"
    RICE = "RICE"
    WSJF = "WSJF"
    MOOSCOW = "MOOSCOW"

class TieResolutionMethod(Enum):
    URGENCY_FIRST = "URGENCY_FIRST"
    IMPACT_FIRST = "IMPACT_FIRST"
    OLDEST_FIRST = "OLDEST_FIRST"
    RANDOM = "RANDOM"

@dataclass(frozen=True)
class PriorityFactor:
    factor_type: PriorityFactorType
    score: float
    weight: float
    evidence: str
    strength: EvidenceStrength

@dataclass(frozen=True)
class PriorityScore:
    total_score: float
    normalized_score: float
    level: PriorityLevel
    urgency: UrgencyLevel
    impact: ImpactLevel
    factors: List[PriorityFactor] = field(default_factory=list)

@dataclass(frozen=True)
class PriorityAssessment:
    assessment_id: str
    method: PrioritizationMethod
    score: PriorityScore
    assessed_at: datetime
    assessor_id: str

@dataclass(frozen=True)
class RecommendationCandidate:
    # Assuming standard fields for the candidate, to be replaced by actual import if exists
    candidate_id: str
    content: str
    workspace_id: str

@dataclass(frozen=True)
class PrioritizedRecommendation:
    candidate: RecommendationCandidate
    assessment: PriorityAssessment
    rank: int

@dataclass(frozen=True)
class RecommendationPrioritizationResult:
    result_id: str
    workspace_id: str
    recommendations: List[PrioritizedRecommendation]
    created_at: datetime
    method_used: PrioritizationMethod
