from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from app.domain.context.models import EntityType, ConflictStatus

class BaseContextSchema(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    version: int
    is_active: bool
    confidence_score: float
    source_system: str
    last_verified_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CustomerContextSchema(BaseContextSchema):
    external_id: str
    tier: Optional[str]
    lifetime_value: float
    risk_profile: Optional[str]

class BusinessOntologySchema(BaseModel):
    internal_concept: str
    display_term: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class KnowledgeGraphEdgeSchema(BaseModel):
    id: uuid.UUID
    source_entity_id: uuid.UUID
    source_entity_type: EntityType
    target_entity_id: uuid.UUID
    target_entity_type: EntityType
    relationship_type: str
    confidence_score: float
    source_system: str
    model_config = ConfigDict(from_attributes=True)

class ContextConflictSchema(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    entity_type: EntityType
    field_name: str
    source_a: str
    value_a: Any
    source_b: str
    value_b: Any
    status: ConflictStatus
    model_config = ConfigDict(from_attributes=True)
    
class ContextDashboardSummary(BaseModel):
    knowledge_completeness: float
    stale_records: int
    conflicts: int
    missing_relationships: int
    ontology_coverage: float
    average_freshness_days: float
