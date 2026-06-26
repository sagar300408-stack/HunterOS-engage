"""
Pydantic schemas for the Intent domain.

IntentResult is the canonical output of every extraction call —
the single source of truth flowing through the pipeline and into the DB.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.intent.models import IntentCategory, UrgencyLevel


# ── Next-action enum ──────────────────────────────────────────────────────────

class NextAction(str):
    """
    Human-readable workflow recommendations produced by the intent engine.
    Used by Phase 5 (Scheduling) and Phase 6 (Follow-up) to trigger automation.
    """
    SCHEDULE_SITE_VISIT      = "Schedule Site Visit"
    CONFIRM_APPOINTMENT      = "Confirm Appointment"
    NOTIFY_SALES_TEAM        = "Notify Sales Team"
    SHARE_PRICING_IMMEDIATELY = "Share Pricing Immediately"
    SEND_PRICING_BROCHURE    = "Send Pricing Brochure"
    SHARE_PRODUCT_DETAILS    = "Share Product Details"
    CREATE_FOLLOWUP          = "Create Follow-up"
    CONTINUE_CONVERSATION    = "Continue Conversation"
    ESCALATE_TO_HUMAN        = "Escalate to Human Agent"
    ANSWER_AND_QUALIFY       = "Answer and Qualify"


# ── Confidence-scored field ───────────────────────────────────────────────────

class ExtractedField(BaseModel):
    """A single extracted fact with its confidence score."""
    value: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ── Core result schema ────────────────────────────────────────────────────────

class IntentResult(BaseModel):
    """
    The structured output of every intent extraction call.

    This is what flows through the pipeline — from intent service
    to AI context builder to intent_history persistence.

    confidence refers to the intent classification itself.
    Each extracted field carries its own confidence score.
    """
    intent: IntentCategory = IntentCategory.other
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    budget:   ExtractedField = Field(default_factory=ExtractedField)
    timeline: ExtractedField = Field(default_factory=ExtractedField)
    interest: ExtractedField = Field(default_factory=ExtractedField)
    location: ExtractedField = Field(default_factory=ExtractedField)

    urgency:      UrgencyLevel = UrgencyLevel.unknown
    buying_stage: Optional[str] = None
    next_action:  Optional[str] = None

    # Raw payload preserved for DB storage
    raw_extraction: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True

    def build_context_block(self) -> str:
        """
        Render this result as the system context string injected into the AI call.
        Only includes fields that were actually extracted (non-null, confidence > 0).
        """
        lines = [
            f"Intent: {self.intent}  (confidence: {self.confidence:.2f})",
            f"Urgency: {self.urgency.title() if hasattr(self.urgency, 'title') else self.urgency}",
        ]
        if self.buying_stage:
            lines.append(f"Buying Stage: {self.buying_stage}")
        if self.budget.value:
            lines.append(f"Budget: {self.budget.value}")
        if self.timeline.value:
            lines.append(f"Timeline: {self.timeline.value}")
        if self.interest.value:
            lines.append(f"Interest: {self.interest.value}")
        if self.location.value:
            lines.append(f"Location: {self.location.value}")
        if self.next_action:
            lines.append(f"Recommended Next Action: {self.next_action}")

        return "\n".join(lines)


# ── DB read schema ────────────────────────────────────────────────────────────

class IntentHistorySchema(BaseModel):
    """Full intent_history row read model."""

    id: UUID
    customer_id: UUID
    conversation_id: UUID
    message_id: UUID

    detected_intent: str
    confidence: float

    budget:             Optional[str]   = None
    budget_confidence:  Optional[float] = None
    timeline:           Optional[str]   = None
    timeline_confidence: Optional[float] = None
    interest:           Optional[str]   = None
    interest_confidence: Optional[float] = None
    location:           Optional[str]   = None
    location_confidence: Optional[float] = None

    urgency:      str
    buying_stage: Optional[str] = None
    next_action:  Optional[str] = None

    extracted_json: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
