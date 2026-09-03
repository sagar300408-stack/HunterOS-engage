"""
HunterOS Engage — Intent Domain Models

intent_history stores every extraction result permanently — one row per message.

Design:
  - Individual columns for the primary fields enable fast SQL dashboard queries
    without parsing JSONB.
  - extracted_json preserves the full raw payload for audit and future fields.
  - message_id FK links every extraction to the exact incoming message.
  - Enums are intentionally broad — new categories are added here, never hacked.

Phase 4 (Dashboard) reads directly from this table.
Phase 5 (Scheduling) queries next_action to trigger automation.
Phase 6 (Follow-up) checks buying_stage + timeline to schedule follow-ups.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base


class IntentCategory(str, enum.Enum):
    product_inquiry       = "Product Inquiry"
    service_inquiry       = "Service Inquiry"
    appointment_request   = "Appointment Request"
    site_visit_request    = "Site Visit Request"
    pricing_request       = "Pricing Request"
    follow_up             = "Follow-up"
    complaint             = "Complaint"
    general_question      = "General Question"
    purchase_ready        = "Purchase Ready"
    information_gathering = "Information Gathering"
    existing_customer     = "Existing Customer"
    other                 = "Other"


class UrgencyLevel(str, enum.Enum):
    high    = "high"
    medium  = "medium"
    low     = "low"
    unknown = "unknown"


class IntentHistory(Base):
    """
    One row per incoming message — the full structured extraction result.

    Never updated after insert — intent is a point-in-time fact about
    what the customer said in that specific message.

    To understand a customer's current state, read the most recent row
    (ordered by created_at DESC) or use get_latest_intent() from the service.
    """

    __tablename__ = "intent_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one extraction per message, always
    )

    # ── Primary extraction fields (individual columns for SQL queries) ─────────
    detected_intent = Column(
        Enum(IntentCategory, name="intentcategory"),
        nullable=False,
        default=IntentCategory.other,
    )
    confidence = Column(Numeric(4, 3), nullable=False, default=0.0)

    budget             = Column(String(255), nullable=True)
    budget_confidence  = Column(Numeric(4, 3), nullable=True)

    timeline           = Column(String(255), nullable=True)
    timeline_confidence = Column(Numeric(4, 3), nullable=True)

    interest           = Column(String(255), nullable=True)
    interest_confidence = Column(Numeric(4, 3), nullable=True)

    location           = Column(String(255), nullable=True)
    location_confidence = Column(Numeric(4, 3), nullable=True)

    urgency     = Column(
        Enum(UrgencyLevel, name="urgencylevel"),
        nullable=False,
        default=UrgencyLevel.unknown,
    )
    buying_stage = Column(String(100), nullable=True)
    next_action  = Column(String(255), nullable=True)
    is_fallback  = Column(Boolean, nullable=False, default=False)

    # ── Full extraction payload ───────────────────────────────────────────────
    extracted_json = Column(JSONB, nullable=True)

    # ── Phase 4: AI Explainability ─────────────────────────────────────────────
    # Why the model reached this classification — shown in the Explainability Panel.
    reasoning         = Column(Text, nullable=True)   # narrative explanation
    memory_influenced = Column(Text, nullable=True)   # which memory facts shaped the classification
    detected_keywords = Column(JSONB, nullable=True)  # list of keyword/phrase matches

    # ── Phase 4: Multi-tenancy ─────────────────────────────────────────────────
    workspace_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    customer     = relationship("Customer", back_populates="intent_history")
    conversation = relationship("Conversation", back_populates="intent_history")
    message      = relationship("Message", back_populates="intent_history")

    __table_args__ = (
        Index("ix_intent_history_customer_id", "customer_id"),
        Index("ix_intent_history_conversation_id", "conversation_id"),
        Index("ix_intent_history_created_at", "created_at"),
        Index("ix_intent_history_detected_intent", "detected_intent"),
    )

    def __repr__(self) -> str:
        return (
            f"<IntentHistory intent={self.detected_intent} "
            f"confidence={self.confidence} customer_id={self.customer_id}>"
        )
