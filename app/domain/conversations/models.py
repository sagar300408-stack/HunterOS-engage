"""
HunterOS Engage — Conversation Domain Models

ORM models for the core communication pipeline.

Schema is intentionally forward-compatible:
  - Phase 2: Add Customer model + Conversation.customer_id FK
  - Phase 3: Add Lead model + Conversation.lead_id FK
  - Phase 5: AIMetadata feeds the analytics dashboard directly
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


class MessageDirection(str, enum.Enum):
    incoming = "incoming"
    outgoing = "outgoing"


class Conversation(Base):
    """
    One conversation per customer session.

    Phase 2: Add customer_id = Column(UUID, ForeignKey("customers.id"), nullable=True)
    """

    __tablename__ = "conversations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    customer_phone = Column(String(30), nullable=False)
    # Phase 2: FK to the customer who owns this conversation.
    # Nullable for backward compatibility with Phase 1 rows.
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Phase 4: workspace_id for multi-tenancy. Default = dev workspace.
    workspace_id = Column(
        UUID(as_uuid=True),
        nullable=True,
    )
    is_demo = Column(Boolean, default=False, server_default="false", nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )

    # Relationships
    customer = relationship("Customer", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        order_by="Message.timestamp",
        cascade="all, delete-orphan",
    )
    intent_history = relationship(
        "IntentHistory",
        back_populates="conversation",
        order_by="IntentHistory.created_at",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_conversations_customer_phone", "customer_phone"),
        Index("ix_conversations_customer_id", "customer_id"),
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} phone={self.customer_phone}>"


class Message(Base):
    """A single message in a conversation — either incoming or outgoing."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    direction = Column(Enum(MessageDirection), nullable=False)
    content = Column(Text, nullable=False)
    # wa_message_id is the deduplication key — unique to prevent double-processing
    wa_message_id = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    ai_metadata = relationship(
        "AIMetadata",
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan",
    )
    intent_history = relationship(
        "IntentHistory",
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan",
    )
    pipeline_events = relationship(
        "PipelineEvent",
        back_populates="message",
        order_by="PipelineEvent.created_at",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("wa_message_id", name="uq_messages_wa_message_id"),
        Index("ix_messages_conversation_id", "conversation_id"),
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} direction={self.direction.value}>"


class AIMetadata(Base):
    """
    Stores full AI response metadata for every outgoing message.

    Powers Phase 5 dashboard metrics:
        - Total conversations handled
        - Average response latency
        - Token usage and cost tracking
        - Model version tracking
        - Prompt version tracking
    """

    __tablename__ = "ai_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)
    finish_reason = Column(String(50), nullable=True)
    prompt_version = Column(String(20), nullable=False, default="v1")

    # Relationship
    message = relationship("Message", back_populates="ai_metadata")
"""
HunterOS Engage — Conversation Domain Models

ORM models for the core communication pipeline.

Schema is intentionally forward-compatible:
  - Phase 2: Add Customer model + Conversation.customer_id FK
  - Phase 3: Add Lead model + Conversation.lead_id FK
  - Phase 5: AIMetadata feeds the analytics dashboard directly
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


class MessageDirection(str, enum.Enum):
    incoming = "incoming"
    outgoing = "outgoing"


class Conversation(Base):
    """
    One conversation per customer session.

    Phase 2: Add customer_id = Column(UUID, ForeignKey("customers.id"), nullable=True)
    """

    __tablename__ = "conversations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    customer_phone = Column(String(30), nullable=False)
    # Phase 2: FK to the customer who owns this conversation.
    # Nullable for backward compatibility with Phase 1 rows.
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Phase 4: workspace_id for multi-tenancy. Default = dev workspace.
    workspace_id = Column(
        UUID(as_uuid=True),
        nullable=True,
    )
    is_demo = Column(Boolean, default=False, server_default="false", nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )

    # Relationships
    customer = relationship("Customer", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        order_by="Message.timestamp",
        cascade="all, delete-orphan",
    )
    intent_history = relationship(
        "IntentHistory",
        back_populates="conversation",
        order_by="IntentHistory.created_at",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_conversations_customer_phone", "customer_phone"),
        Index("ix_conversations_customer_id", "customer_id"),
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} phone={self.customer_phone}>"


class Message(Base):
    """A single message in a conversation — either incoming or outgoing."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    direction = Column(Enum(MessageDirection), nullable=False)
    content = Column(Text, nullable=False)
    # wa_message_id is the deduplication key — unique to prevent double-processing
    wa_message_id = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    ai_metadata = relationship(
        "AIMetadata",
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan",
    )
    intent_history = relationship(
        "IntentHistory",
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan",
    )
    pipeline_events = relationship(
        "PipelineEvent",
        back_populates="message",
        order_by="PipelineEvent.created_at",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("wa_message_id", name="uq_messages_wa_message_id"),
        Index("ix_messages_conversation_id", "conversation_id"),
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} direction={self.direction.value}>"


class AIMetadata(Base):
    """
    Stores full AI response metadata for every outgoing message.

    Powers Phase 5 dashboard metrics:
        - Total conversations handled
        - Average response latency
        - Token usage and cost tracking
        - Model version tracking
        - Prompt version tracking
    """

    __tablename__ = "ai_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)
    finish_reason = Column(String(50), nullable=True)
    prompt_version = Column(String(20), nullable=False, default="v1")

    # Relationship
    message = relationship("Message", back_populates="ai_metadata")

    def __repr__(self) -> str:
        return (
            f"<AIMetadata message_id={self.message_id} "
            f"model={self.model} tokens={self.total_tokens}>"
        )
# Import at bottom to avoid circular dependencies and ensure relationships can resolve
from app.domain.dashboard.models import PipelineEvent
from app.domain.intent.models import IntentHistory
