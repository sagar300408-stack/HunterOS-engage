from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.recommendations.models import (
    RecommendationType,
    RecommendationStatus,
    RecommendationSource,
    RecommendationScope,
    RecommendationPriority
)
from app.domain.recommendations.evidence.models import EvidenceType

class RecommendationConfidenceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: float = Field(ge=0.0, le=1.0)

class RecommendationActorContextDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    actor_id: str
    actor_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RecommendationTargetDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    target_id: str
    target_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EvidenceReferenceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    reference_id: str
    reference_type: str
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RecommendationEvidenceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID
    recommendation_id: UUID
    type: EvidenceType
    reference: EvidenceReferenceDTO
    relevance_score: float = Field(ge=0.0, le=1.0)
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

class RecommendationProvenanceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    provenance_id: UUID
    workspace_id: UUID
    source_modules: List[str]
    source_artifact_ids: List[UUID]
    generated_by: str
    generation_method: str
    pipeline_version: str
    engine_version: str
    schema_version: str
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

class RecommendationDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID
    workspace_id: UUID
    type: RecommendationType
    status: RecommendationStatus
    source: RecommendationSource
    scope: RecommendationScope
    priority: RecommendationPriority
    confidence: RecommendationConfidenceDTO
    title: str
    description: str
    action_url: Optional[str] = None
    actor_context: Optional[RecommendationActorContextDTO] = None
    targets: List[RecommendationTargetDTO] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class CreateRecommendationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    workspace_id: UUID
    type: RecommendationType
    source: RecommendationSource
    scope: RecommendationScope
    priority: RecommendationPriority
    confidence: float = Field(ge=0.0, le=1.0)
    title: str
    description: str
    action_url: Optional[str] = None
    actor_context: Optional[RecommendationActorContextDTO] = None
    targets: List[RecommendationTargetDTO] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UpdateRecommendationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[RecommendationPriority] = None
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ChangeRecommendationStatusRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: RecommendationStatus

class RecommendationQueryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    workspace_id: UUID
    types: Optional[List[RecommendationType]] = None
    statuses: Optional[List[RecommendationStatus]] = None
    scopes: Optional[List[RecommendationScope]] = None
    priorities: Optional[List[RecommendationPriority]] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class RecommendationListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: List[RecommendationDTO]
    total: int

class RecommendationDetectionResultDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    workspace_id: UUID
    target_id: Optional[str] = None
    candidates: List[Dict[str, Any]] = Field(default_factory=list)

