import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, Enum, Boolean, Integer, Float,
    JSON, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.domain.conversations.models import Base


# ── Edition / Plan ─────────────────────────────────────────────────────────────

class Edition(str, enum.Enum):
    starter = "starter"
    professional = "professional"
    enterprise = "enterprise"
    trial = "trial"


# ── License ────────────────────────────────────────────────────────────────────

class LicenseStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    suspended = "suspended"
    trial = "trial"

class License(Base):
    """
    Controls feature entitlements and seat limits per organization.
    Feature access is driven entirely by this record, not hardcoded logic.
    """
    __tablename__ = "commercial_licenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    edition = Column(Enum(Edition, name="edition"), nullable=False, default=Edition.trial)
    status = Column(Enum(LicenseStatus, name="licensestatus"), nullable=False, default=LicenseStatus.trial)

    seat_limit = Column(Integer, nullable=False, default=10)
    
    # JSON map of feature flags, e.g. {"ai_recommendations": true, "integrations": 3}
    entitlements = Column(JSONB, nullable=False, default=dict)

    issued_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = ()


# ── Subscription ───────────────────────────────────────────────────────────────

class SubscriptionStatus(str, enum.Enum):
    active = "active"
    past_due = "past_due"
    cancelled = "cancelled"
    trialing = "trialing"

class Subscription(Base):
    """
    Recurring billing relationship for a workspace.
    """
    __tablename__ = "commercial_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    license_id = Column(UUID(as_uuid=True), ForeignKey("commercial_licenses.id"), nullable=False)

    plan_name = Column(String(100), nullable=False)
    billing_cycle = Column(String(20), nullable=False, default="annual")  # monthly | annual

    amount_usd = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="USD")

    status = Column(Enum(SubscriptionStatus, name="subscriptionstatus"), nullable=False, default=SubscriptionStatus.trialing)

    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())


# ── Invoice ────────────────────────────────────────────────────────────────────

class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    issued = "issued"
    paid = "paid"
    overdue = "overdue"
    void = "void"

class Invoice(Base):
    """
    Formal billing record issued to a customer per billing cycle.
    """
    __tablename__ = "commercial_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("commercial_subscriptions.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    invoice_number = Column(String(50), nullable=False, unique=True)
    amount_usd = Column(Float, nullable=False)
    
    status = Column(Enum(InvoiceStatus, name="invoicestatus"), nullable=False, default=InvoiceStatus.draft)

    issued_at = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    line_items = Column(JSONB, nullable=False, default=list)


# ── Sales Pipeline ─────────────────────────────────────────────────────────────

class PipelineStage(str, enum.Enum):
    lead = "lead"
    qualified = "qualified"
    discovery = "discovery"
    solution_design = "solution_design"
    proposal = "proposal"
    negotiation = "negotiation"
    pilot = "pilot"
    closed_won = "closed_won"
    closed_lost = "closed_lost"

class SalesPipelineLead(Base):
    """
    Tracks the B2B sales journey from lead to commercial customer.
    """
    __tablename__ = "commercial_sales_pipeline"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    
    stage = Column(Enum(PipelineStage, name="pipelinestage"), nullable=False, default=PipelineStage.lead)
    
    estimated_arr_usd = Column(Float, nullable=True)
    
    win_probability = Column(Float, nullable=True)  # 0.0 – 1.0
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    stage_updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.utcnow())
    
    notes = Column(JSONB, nullable=False, default=list)
