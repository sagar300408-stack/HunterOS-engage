"""
HunterOS Engage — Scheduling Domain Models

Phase 5: Four new tables introduced by the Scheduling Engine.

  scheduled_events                  — All scheduled business events (generic, single table)
  scheduling_candidates             — AI-proposed events awaiting information collection
  event_audit_log                   — Immutable per-event change trail
  customer_availability_preferences — Customer scheduling preferences

Design:
  - event_type is a String column, NOT a DB Enum — allows new types without migrations
  - status is enforced by state_machine.py, not DB-level constraints
  - metadata JSONB stores event-type-specific fields (see metadata_accessors.py)
  - follow_up_policy JSONB is reserved for Phase 6 — always null in Phase 5
  - All tables carry workspace_id for multi-tenancy
  - No separate tables per event type (no meetings, callbacks, site_visits)
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base
from app.domain.dashboard.models import DEFAULT_WORKSPACE_ID


# ── ScheduledEvent ─────────────────────────────────────────────────────────────

class ScheduledEvent(Base):
    """
    Generic scheduled business event.

    One row per event regardless of type. event_type string distinguishes
    the kind of event. event-specific data lives in metadata JSONB.

    Status lifecycle is enforced by state_machine.py — do not set .status directly.
    Use scheduling service methods: confirm_event(), complete_event(), etc.

    Supported event_type values (extensible — add to resolver.py, not here):
        meeting | site_visit | callback | followup | reminder | task
    """
    __tablename__ = "scheduled_events"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Core fields ───────────────────────────────────────────────────────────
    event_type  = Column(String(50),  nullable=False)                # "meeting", "site_visit", etc.
    title       = Column(String(255), nullable=False)
    description = Column(Text,        nullable=True)

    # Status — values: pending | confirmed | in_progress | completed | cancelled | rescheduled
    # Transitions enforced by state_machine.py
    status   = Column(String(50), nullable=False, default="pending")
    priority = Column(String(20), nullable=False, default="medium")  # high | medium | low

    # Scheduling
    scheduled_for    = Column(DateTime(timezone=True), nullable=True)   # NULL = "time TBD"
    duration_minutes = Column(Integer, nullable=True)

    # Assignment
    assignment_strategy = Column(String(50), nullable=False, default="manual")

    # AI tracking
    created_by_ai = Column(Boolean, nullable=False, default=False)

    # CRM sync
    crm_synced            = Column(Boolean, nullable=False, default=False)
    crm_provider_event_id = Column(String(255), nullable=True)   # external provider event ID

    # Flexible payload
    event_metadata   = Column("metadata", JSONB, nullable=True)   # event-type-specific fields
    follow_up_policy = Column(JSONB, nullable=True)   # Phase 6 extension point — null in Phase 5

    # Demo / multi-tenant
    is_demo = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at   = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    updated_at   = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    customer     = relationship("Customer",      foreign_keys=[customer_id],  backref="scheduled_events")
    conversation = relationship("Conversation",  foreign_keys=[conversation_id])
    assignee     = relationship("User",          foreign_keys=[assigned_to])
    creator      = relationship("User",          foreign_keys=[created_by])
    audit_log    = relationship(
        "EventAuditLog",
        back_populates="event",
        order_by="EventAuditLog.created_at",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_scheduled_events_workspace_id",  "workspace_id"),
        Index("ix_scheduled_events_customer_id",   "customer_id"),
        Index("ix_scheduled_events_status",        "status"),
        Index("ix_scheduled_events_event_type",    "event_type"),
        Index("ix_scheduled_events_scheduled_for", "scheduled_for"),
        Index("ix_scheduled_events_assigned_to",   "assigned_to"),
        Index("ix_scheduled_events_created_at",    "created_at"),
    )

    def get_typed_metadata(self):
        """Return metadata as a typed Pydantic model for this event_type."""
        from app.domain.scheduling.metadata_accessors import parse_metadata
        return parse_metadata(self.event_type, self.event_metadata or {})

    def __repr__(self) -> str:
        return (
            f"<ScheduledEvent type={self.event_type} status={self.status} "
            f"customer_id={self.customer_id}>"
        )


# ── SchedulingCandidate ────────────────────────────────────────────────────────

class SchedulingCandidate(Base):
    """
    AI-proposed scheduling event awaiting information collection.

    Lifecycle:
        pending_info  → AI is collecting missing required fields via follow-up questions
        ready         → All required fields collected, ready to promote
        promoted      → Became a ScheduledEvent (see promoted_event_id)
        abandoned     → Timed out or manually abandoned

    The pipeline checks for an active candidate after intent extraction
    and injects a PENDING SCHEDULING REQUEST block into the AI system prompt,
    directing the AI to ask for the missing fields naturally.
    """
    __tablename__ = "scheduling_candidates"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)

    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    promoted_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scheduled_events.id", ondelete="SET NULL"),
        nullable=True,
    )

    suggested_event_type = Column(String(50),  nullable=False)
    suggested_title      = Column(String(255), nullable=True)

    # Resolver output — full decision context
    resolver_output = Column(JSONB, nullable=True)

    # Field collection state
    collected_data = Column(JSONB, nullable=False, default=dict)  # fields collected so far
    missing_fields = Column(JSONB, nullable=False, default=list)  # required fields still needed

    # Status: pending_info | ready | promoted | abandoned
    status = Column(String(30), nullable=False, default="pending_info")

    created_by_ai = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())

    # ── Relationships ─────────────────────────────────────────────────────────
    customer       = relationship("Customer",       foreign_keys=[customer_id])
    conversation   = relationship("Conversation",   foreign_keys=[conversation_id])
    promoted_event = relationship("ScheduledEvent", foreign_keys=[promoted_event_id])

    __table_args__ = (
        Index("ix_scheduling_candidates_workspace_id",  "workspace_id"),
        Index("ix_scheduling_candidates_customer_id",   "customer_id"),
        Index("ix_scheduling_candidates_status",        "status"),
        Index("ix_scheduling_candidates_created_at",    "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SchedulingCandidate type={self.suggested_event_type} "
            f"status={self.status} missing={self.missing_fields}>"
        )


# ── EventAuditLog ──────────────────────────────────────────────────────────────

class EventAuditLog(Base):
    """
    Immutable per-event change trail.

    One row per mutation — never updated after insert.
    Every state change, assignment, reschedule is recorded here.

    Used by:
        - GET /scheduling/events/{id}/audit-log  (event detail view)
        - Manager dashboards for accountability
        - Debugging scheduling workflows
    """
    __tablename__ = "event_audit_log"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)

    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scheduled_events.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Who performed the action
    actor_type = Column(String(20),  nullable=False, default="system")  # user | ai | system
    actor_id   = Column(UUID(as_uuid=True), nullable=True)              # None for AI/system

    # What happened
    action      = Column(String(100), nullable=False)  # created | assigned | confirmed | completed | cancelled | rescheduled | updated
    from_status = Column(String(50),  nullable=True)   # status before
    to_status   = Column(String(50),  nullable=True)   # status after

    # Before/after diff or context
    payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow())

    # ── Relationships ─────────────────────────────────────────────────────────
    event = relationship("ScheduledEvent", back_populates="audit_log")

    __table_args__ = (
        Index("ix_event_audit_log_event_id",     "event_id"),
        Index("ix_event_audit_log_workspace_id", "workspace_id"),
        Index("ix_event_audit_log_created_at",   "created_at"),
        Index("ix_event_audit_log_action",        "action"),
    )

    def __repr__(self) -> str:
        return f"<EventAuditLog action={self.action} event_id={self.event_id}>"


# ── CustomerAvailabilityPreferences ───────────────────────────────────────────

class CustomerAvailabilityPreferences(Base):
    """
    Customer scheduling preferences — soft hints used by the Scheduling Engine.

    These are PREFERENCES, not hard constraints. The engine uses them to:
        - Warn when a proposed time conflicts with preferences
        - Guide the AI when asking "when works for you?"

    Never hard-blocks scheduling — the sales team always has override authority.
    """
    __tablename__ = "customer_availability_preferences"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, default=DEFAULT_WORKSPACE_ID)

    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one row per customer
    )

    preferred_time_of_day  = Column(String(20),  nullable=True)   # morning | afternoon | evening | any
    unavailable_days       = Column(JSONB,        nullable=True)   # ["Sunday", "Saturday"]
    preferred_meeting_mode = Column(String(20),  nullable=True)   # in_person | online | phone | any
    timezone               = Column(String(50),  nullable=False, default="Asia/Kolkata")
    notes                  = Column(Text,         nullable=True)   # free text

    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())

    # ── Relationships ─────────────────────────────────────────────────────────
    customer = relationship("Customer", foreign_keys=[customer_id])

    __table_args__ = (
        Index("ix_customer_availability_prefs_workspace_id", "workspace_id"),
        Index("ix_customer_availability_prefs_customer_id",  "customer_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<CustomerAvailabilityPreferences customer_id={self.customer_id} "
            f"mode={self.preferred_meeting_mode} time={self.preferred_time_of_day}>"
        )
