"""
HunterOS Engage — Memory Domain Models

Three tables form the memory system:

  CustomerMemory          — Latest extracted knowledge (mutable, always current)
  CustomerMemoryVersion   — Immutable snapshot archive (written before every update)
  CustomerMemoryEvent     — Append-only event log (full customer lifecycle)

Design:
  - CustomerMemory holds structured_data as JSONB for flexible schema evolution.
  - CustomerMemoryVersion snapshots the full state before every overwrite,
    enabling rollback, auditing, and hallucination recovery.
  - CustomerMemoryEvent is the foundation for Phase 5 activity feeds and dashboards.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

from app.domain.conversations.models import Base


class MemoryEventType(str, enum.Enum):
    customer_created = "customer_created"
    customer_updated = "customer_updated"
    budget_detected = "budget_detected"
    timeline_detected = "timeline_detected"
    interest_detected = "interest_detected"
    location_detected = "location_detected"
    memory_summarized = "memory_summarized"
    memory_version_created = "memory_version_created"
    conversation_started = "conversation_started"
    lead_status_changed = "lead_status_changed"


class CustomerMemory(Base):
    """
    Latest extracted knowledge for a customer.

    Always contains the most recent AI-generated summary and
    confidence-scored structured fields. Overwritten on each memory update;
    a snapshot is first written to CustomerMemoryVersion.

    structured_data format:
    {
        "budget":             {"value": "₹80L",         "confidence": 0.96},
        "timeline":           {"value": "6 months",     "confidence": 0.72},
        "preferred_location": {"value": "North Bangalore","confidence": 0.88},
        "interests": [
            {"value": "residential plots", "confidence": 0.95}
        ]
    }
    """

    __tablename__ = "customer_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    summary = Column(Text, nullable=True)
    structured_data = Column(JSONB, nullable=True, default=dict)
    # Tracks total messages seen — drives the update interval check
    message_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="memory")

    def __repr__(self) -> str:
        return f"<CustomerMemory customer_id={self.customer_id} messages={self.message_count}>"


class CustomerMemoryVersion(Base):
    """
    Immutable snapshot of CustomerMemory, written before every update.

    Enables:
        - Memory rollback after AI hallucination
        - Full audit trail of how the AI's understanding evolved
        - Future analytics on memory drift over time
    """

    __tablename__ = "customer_memory_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary = Column(Text, nullable=True)
    structured_data = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="memory_versions")

    __table_args__ = (
        Index("ix_memory_versions_customer_id", "customer_id"),
    )

    def __repr__(self) -> str:
        return f"<CustomerMemoryVersion customer_id={self.customer_id} at={self.created_at}>"


class CustomerMemoryEvent(Base):
    """
    Append-only event log for the full customer lifecycle.

    Never updated or deleted — only inserted.

    Powers Phase 5 features:
        - Activity Feed
        - Customer Journey Timeline
        - Executive Dashboard
        - Lead Stage History

    payload examples:
        customer_created:    {"phone": "+91...", "name": "Rahul"}
        budget_detected:     {"value": "₹80L", "confidence": 0.96}
        memory_summarized:   {"trigger": "interval", "message_count": 5}
        conversation_started:{"conversation_id": "uuid", "idle_hours": 26}
    """

    __tablename__ = "customer_memory_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(
        Enum(MemoryEventType, name="memoryeventtype"),
        nullable=False,
    )
    payload = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="memory_events")

    __table_args__ = (
        Index("ix_memory_events_customer_id", "customer_id"),
        Index("ix_memory_events_event_type", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<CustomerMemoryEvent type={self.event_type} customer_id={self.customer_id}>"
