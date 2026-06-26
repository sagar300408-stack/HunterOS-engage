"""
HunterOS Engage — Customer Domain Models

The Customer is the root entity for every future module:
  - Phase 2: CustomerMemory, CustomerMemoryVersion, CustomerMemoryEvent
  - Phase 3: IntentHistory, buying_stage sync
  - Phase 4: Dashboard analytics grouped by customer
  - Phase 5: Scheduling, CRM integration

Schema is additive — no existing column is removed.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base


class CustomerStatus(str, enum.Enum):
    new = "new"
    active = "active"
    inactive = "inactive"
    qualified = "qualified"


class Customer(Base):
    """
    Persistent customer profile.

    One row per unique phone number — never duplicated.

    Relationships:
        conversations  → all Conversation rows for this customer
        memory         → single CustomerMemory (latest extracted knowledge)
        memory_events  → full CustomerMemoryEvent log
    """

    __tablename__ = "customers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    phone = Column(String(30), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    status = Column(
        Enum(CustomerStatus, name="customerstatus"),
        nullable=False,
        default=CustomerStatus.new,
    )
    preferred_language = Column(String(10), nullable=False, default="en")
    notes = Column(Text, nullable=True)
    # Phase 3: Synced from latest IntentHistory.buying_stage after every extraction.
    # Enables fast dashboard queries without joining intent_history.
    buying_stage = Column(String(100), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )
    last_interaction = Column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    conversations = relationship(
        "Conversation",
        back_populates="customer",
        order_by="Conversation.created_at",
    )
    memory = relationship(
        "CustomerMemory",
        back_populates="customer",
        uselist=False,
        cascade="all, delete-orphan",
    )
    memory_versions = relationship(
        "CustomerMemoryVersion",
        back_populates="customer",
        order_by="CustomerMemoryVersion.created_at",
        cascade="all, delete-orphan",
    )
    memory_events = relationship(
        "CustomerMemoryEvent",
        back_populates="customer",
        order_by="CustomerMemoryEvent.created_at",
        cascade="all, delete-orphan",
    )
    intent_history = relationship(
        "IntentHistory",
        back_populates="customer",
        order_by="IntentHistory.created_at",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_customers_phone", "phone"),
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} phone={self.phone} status={self.status}>"
