import uuid
import enum
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import Column, String, DateTime, JSON, Float, ForeignKey, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_mixin, declared_attr, relationship

from app.domain.conversations.models import Base

class EntityType(str, enum.Enum):
    ORGANIZATION = "ORGANIZATION"
    PRODUCT = "PRODUCT"
    WORKFLOW = "WORKFLOW"
    POLICY = "POLICY"
    CUSTOMER = "CUSTOMER"
    TEAM_MEMBER = "TEAM_MEMBER"
    DOCUMENT = "DOCUMENT"

class ConflictStatus(str, enum.Enum):
    UNRESOLVED = "UNRESOLVED"
    RESOLVED_MANUAL = "RESOLVED_MANUAL"
    RESOLVED_AUTO = "RESOLVED_AUTO"

@declarative_mixin
class VersionedContextMixin:
    """Mixin to provide versioning for context entities."""
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    valid_from = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    valid_to = Column(DateTime(timezone=True), nullable=True)

@declarative_mixin
class QualityContextMixin:
    """Mixin to provide confidence, freshness, and source tracking."""
    confidence_score = Column(Float, default=1.0, nullable=False) # 0.0 to 1.0
    source_system = Column(String, nullable=False) # e.g. "CRM", "ERP", "MANUAL"
    last_verified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    stale_threshold_days = Column(Integer, default=90, nullable=False)

# -----------------
# Entities
# -----------------

class OrganizationNode(Base, VersionedContextMixin, QualityContextMixin):
    __tablename__ = "context_organization_nodes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    node_type = Column(String, nullable=False) # e.g., "Department", "Team", "Role"
    name = Column(String, nullable=False)
    metadata_data = Column(JSON, default=dict)

class ProductService(Base, VersionedContextMixin, QualityContextMixin):
    __tablename__ = "context_product_services"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    item_type = Column(String, nullable=False) # "Product", "Service"
    name = Column(String, nullable=False)
    pricing_rules = Column(JSON, default=dict)
    eligibility_rules = Column(JSON, default=dict)

class WorkflowDefinition(Base, VersionedContextMixin, QualityContextMixin):
    __tablename__ = "context_workflow_definitions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    name = Column(String, nullable=False)
    stages = Column(JSON, default=list)

class BusinessPolicy(Base, VersionedContextMixin, QualityContextMixin):
    __tablename__ = "context_business_policies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    policy_type = Column(String, nullable=False) # e.g., "Discount", "Refund", "SLA"
    rules = Column(JSON, default=dict)

class CustomerContext(Base, VersionedContextMixin, QualityContextMixin):
    __tablename__ = "context_customers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    external_id = Column(String, nullable=False)
    tier = Column(String, nullable=True)
    lifetime_value = Column(Float, default=0.0)
    risk_profile = Column(String, nullable=True)

class TeamMemberContext(Base, VersionedContextMixin, QualityContextMixin):
    __tablename__ = "context_team_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    skills = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    territories = Column(JSON, default=list)

class KnowledgeDocument(Base, VersionedContextMixin, QualityContextMixin):
    __tablename__ = "context_knowledge_documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    doc_type = Column(String, nullable=False) # e.g., "SOP", "FAQ"
    title = Column(String, nullable=False)
    extracted_knowledge = Column(JSON, default=dict)

class BusinessOntology(Base):
    __tablename__ = "context_business_ontology"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    internal_concept = Column(String, nullable=False) # e.g., "Customer"
    display_term = Column(String, nullable=False)     # e.g., "Client"
    is_active = Column(Boolean, default=True)

# -----------------
# Graph Edges & Conflicts
# -----------------

class KnowledgeGraphEdge(Base):
    __tablename__ = "context_graph_edges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    
    source_entity_id = Column(UUID(as_uuid=True), nullable=False)
    source_entity_type = Column(SQLEnum(EntityType), nullable=False)
    
    target_entity_id = Column(UUID(as_uuid=True), nullable=False)
    target_entity_type = Column(SQLEnum(EntityType), nullable=False)
    
    relationship_type = Column(String, nullable=False) # e.g., "PURCHASED", "REPORTS_TO"
    confidence_score = Column(Float, default=1.0)
    source_system = Column(String, nullable=False) # "CRM", "INFERENCE_ENGINE"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ContextConflict(Base):
    __tablename__ = "context_conflicts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    field_name = Column(String, nullable=False)
    
    source_a = Column(String, nullable=False)
    value_a = Column(JSON, nullable=False)
    
    source_b = Column(String, nullable=False)
    value_b = Column(JSON, nullable=False)
    
    status = Column(SQLEnum(ConflictStatus), default=ConflictStatus.UNRESOLVED)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
