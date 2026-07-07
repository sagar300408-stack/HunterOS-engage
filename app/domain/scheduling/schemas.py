"""
HunterOS Engage — Scheduling Domain Pydantic Schemas

All request/response models for scheduling API endpoints.

Naming conventions:
  - *Request  — incoming API body (POST / PUT / PATCH)
  - *Response — outgoing API response
  - *Summary  — lightweight list item
  - *Detail   — full object with nested relations
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Shared sub-models ──────────────────────────────────────────────────────────

class EventAuditLogEntry(BaseModel):
    """One row from event_audit_log."""
    id:          UUID
    actor_type:  str
    actor_id:    Optional[UUID]
    action:      str
    from_status: Optional[str]
    to_status:   Optional[str]
    payload:     Optional[dict[str, Any]]
    created_at:  datetime

    model_config = {"from_attributes": True}


class ConflictEventSummary(BaseModel):
    """Minimal summary of a conflicting event returned in conflict results."""
    id:            UUID
    title:         str
    event_type:    str
    scheduled_for: Optional[datetime]
    duration_minutes: Optional[int]
    status:        str

    model_config = {"from_attributes": True}


class ConflictCheckResponse(BaseModel):
    """Response for POST /scheduling/events/check-conflicts."""
    has_conflict:        bool
    conflicting_events:  list[ConflictEventSummary]
    suggested_slots:     list[datetime]       # Phase 6 — always empty in Phase 5
    checked_user_id:     Optional[UUID]
    checked_time:        Optional[datetime]
    checked_duration_min: Optional[int]


# ── ScheduledEvent schemas ─────────────────────────────────────────────────────

class CreateEventRequest(BaseModel):
    """
    Request body for POST /scheduling/events.

    Only event_type and title are required.
    metadata is event-type-specific (see metadata_accessors.py).
    assigned_to is optional — unassigned events are valid.
    """
    event_type:         str                     = Field(..., description="meeting | site_visit | callback | followup | reminder | task")
    title:              str                     = Field(..., min_length=1, max_length=255)
    description:        Optional[str]           = None
    customer_id:        Optional[UUID]          = None
    conversation_id:    Optional[UUID]          = None
    assigned_to:        Optional[UUID]          = None
    priority:           str                     = Field("medium", pattern="^(high|medium|low)$")
    scheduled_for:      Optional[datetime]      = None
    duration_minutes:   Optional[int]           = Field(None, ge=0, le=1440)
    assignment_strategy: str                    = Field("manual", description="manual | round_robin | ai | territory | skill_based")
    metadata:           Optional[dict[str, Any]] = None
    workspace_id:       Optional[UUID]          = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        valid = {"meeting", "site_visit", "callback", "followup", "reminder", "task"}
        if v not in valid:
            raise ValueError(f"event_type must be one of: {sorted(valid)}")
        return v


class UpdateEventRequest(BaseModel):
    """
    Request body for PATCH /scheduling/events/{id}.

    All fields optional — partial update (PATCH semantics).
    Status changes must go through dedicated transition endpoints.
    """
    title:            Optional[str]            = Field(None, min_length=1, max_length=255)
    description:      Optional[str]            = None
    assigned_to:      Optional[UUID]           = None
    priority:         Optional[str]            = Field(None, pattern="^(high|medium|low)$")
    scheduled_for:    Optional[datetime]       = None
    duration_minutes: Optional[int]            = Field(None, ge=0, le=1440)
    metadata:         Optional[dict[str, Any]] = None


class TransitionEventRequest(BaseModel):
    """
    Request body for POST /scheduling/events/{id}/transition.

    Applies a state machine transition. The service validates the transition.
    """
    new_status: str    = Field(..., description="confirmed | in_progress | completed | cancelled | rescheduled")
    note:       Optional[str] = Field(None, description="Optional reason / note logged to audit trail")


class RescheduleEventRequest(BaseModel):
    """
    Request body for POST /scheduling/events/{id}/reschedule.

    Marks the original event as 'rescheduled' (terminal) and creates a new
    ScheduledEvent with the updated time, copying all other fields.
    """
    new_scheduled_for:    datetime
    new_duration_minutes: Optional[int] = None
    reason:               Optional[str] = None


class AssignEventRequest(BaseModel):
    """Request body for POST /scheduling/events/{id}/assign."""
    assigned_to:         UUID
    assignment_strategy: str = Field("manual", description="manual | round_robin | ai")
    note:                Optional[str] = None


class ConflictCheckRequest(BaseModel):
    """Request body for POST /scheduling/events/check-conflicts."""
    assigned_to:      UUID
    scheduled_for:    datetime
    duration_minutes: int  = Field(60, ge=1, le=1440)
    exclude_event_id: Optional[UUID] = None
    workspace_id:     Optional[UUID] = None


class EventSummary(BaseModel):
    """
    Lightweight event summary for list views.

    Returned by GET /scheduling/events (paginated list).
    """
    id:               UUID
    workspace_id:     UUID
    customer_id:      Optional[UUID]
    conversation_id:  Optional[UUID]
    assigned_to:      Optional[UUID]
    event_type:       str
    title:            str
    status:           str
    priority:         str
    scheduled_for:    Optional[datetime]
    duration_minutes: Optional[int]
    created_by_ai:    bool
    crm_synced:       bool
    is_demo:          bool
    created_at:       datetime
    updated_at:       datetime

    model_config = {"from_attributes": True}


class EventDetail(BaseModel):
    """
    Full event object for GET /scheduling/events/{id}.

    Includes audit log and typed metadata.
    """
    id:                   UUID
    workspace_id:         UUID
    customer_id:          Optional[UUID]
    conversation_id:      Optional[UUID]
    assigned_to:          Optional[UUID]
    created_by:           Optional[UUID]
    event_type:           str
    title:                str
    description:          Optional[str]
    status:               str
    priority:             str
    scheduled_for:        Optional[datetime]
    duration_minutes:     Optional[int]
    assignment_strategy:  str
    created_by_ai:        bool
    crm_provider_event_id: Optional[str]
    metadata:             Optional[dict[str, Any]] = Field(None, validation_alias="event_metadata", alias="event_metadata")
    follow_up_policy:     Optional[dict[str, Any]]
    is_demo:              bool
    created_at:           datetime
    updated_at:           datetime
    completed_at:         Optional[datetime]
    cancelled_at:         Optional[datetime]
    audit_log:            list[EventAuditLogEntry] = Field(default_factory=list)
    allowed_transitions:  list[str]                = Field(default_factory=list)

    model_config = {"from_attributes": True, "populate_by_name": True}


class EventPage(BaseModel):
    """Paginated list of scheduled events."""
    items:     list[EventSummary]
    total:     int
    page:      int
    page_size: int
    has_next:  bool


class EventResponse(BaseModel):
    """Single event response — used after create, update, and transition."""
    event:   EventDetail
    message: str = "OK"


# ── SchedulingCandidate schemas ────────────────────────────────────────────────

class CandidateSummary(BaseModel):
    """Lightweight candidate for list views."""
    id:                   UUID
    workspace_id:         UUID
    customer_id:          UUID
    conversation_id:      Optional[UUID]
    suggested_event_type: str
    suggested_title:      Optional[str]
    status:               str
    missing_fields:       list[str]
    created_at:           datetime
    updated_at:           datetime

    model_config = {"from_attributes": True}


class CandidateDetail(BaseModel):
    """Full candidate detail for GET /scheduling/candidates/{id}."""
    id:                   UUID
    workspace_id:         UUID
    customer_id:          UUID
    conversation_id:      Optional[UUID]
    promoted_event_id:    Optional[UUID]
    suggested_event_type: str
    suggested_title:      Optional[str]
    resolver_output:      Optional[dict[str, Any]]
    collected_data:       dict[str, Any]
    missing_fields:       list[str]
    status:               str
    created_by_ai:        bool
    created_at:           datetime
    updated_at:           datetime

    model_config = {"from_attributes": True}


class UpdateCandidateRequest(BaseModel):
    """
    Request body for PATCH /scheduling/candidates/{id}.

    Supplies newly collected field values.
    The service merges these into collected_data and re-evaluates missing_fields.
    If missing_fields becomes empty, the candidate transitions to 'ready'.
    """
    collected_data: dict[str, Any] = Field(..., description="Fields collected so far — merged with existing")


class PromoteCandidateResponse(BaseModel):
    """Response after promoting a candidate to a ScheduledEvent."""
    candidate:  CandidateDetail
    event:      EventDetail
    message:    str = "Candidate promoted to ScheduledEvent"


# ── CustomerAvailabilityPreferences schemas ────────────────────────────────────

class AvailabilityPreferencesRequest(BaseModel):
    """Request body for PUT /scheduling/customers/{id}/availability."""
    preferred_time_of_day:  Optional[str]       = Field(None, description="morning | afternoon | evening | any")
    unavailable_days:       Optional[list[str]] = Field(None, description='e.g. ["Sunday", "Saturday"]')
    preferred_meeting_mode: Optional[str]       = Field(None, description="in_person | online | phone | any")
    timezone:               Optional[str]       = Field(None, description='e.g. "Asia/Kolkata"')
    notes:                  Optional[str]       = None


class AvailabilityPreferencesResponse(BaseModel):
    """Response for GET/PUT /scheduling/customers/{id}/availability."""
    id:                     UUID
    customer_id:            UUID
    workspace_id:           UUID
    preferred_time_of_day:  Optional[str]
    unavailable_days:       Optional[list[str]]
    preferred_meeting_mode: Optional[str]
    timezone:               str
    notes:                  Optional[str]
    updated_at:             datetime

    model_config = {"from_attributes": True}


# ── Resolver schemas ───────────────────────────────────────────────────────────

class ResolverRequest(BaseModel):
    """
    Request body for POST /scheduling/resolve.

    Runs the resolver without creating any DB records.
    Useful for dashboard previews and intent pipeline hooks.
    """
    next_action:    Optional[str]  = None
    buying_stage:   Optional[str]  = None
    urgency:        Optional[str]  = None
    confidence:     float          = Field(0.0, ge=0.0, le=1.0)
    customer_name:  Optional[str]  = None
    extracted_data: Optional[dict[str, Any]] = None


class ResolverResponse(BaseModel):
    """
    Response from POST /scheduling/resolve.

    decision=None means no scheduling action is warranted.
    """
    matched:              bool
    decision:             Optional[dict[str, Any]] = None
    suggested_event_type: Optional[str]            = None
    suggested_title:      Optional[str]            = None
    missing_fields:       list[str]                = Field(default_factory=list)
    can_create_immediately: bool                   = False


# ── Scheduling overview (dashboard widget) ─────────────────────────────────────

class SchedulingOverview(BaseModel):
    """
    High-level scheduling KPIs for the dashboard.

    Returned by GET /scheduling/overview.
    """
    total_events:           int
    pending:                int
    confirmed:              int
    in_progress:            int
    completed_today:        int
    cancelled_today:        int
    active_candidates:      int
    events_this_week:       int
    overdue_events:         int     # scheduled_for < now AND status in (pending, confirmed)
    ai_created_percentage:  float   # % of events created by AI vs manually
