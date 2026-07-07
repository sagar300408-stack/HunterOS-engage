"""
HunterOS Engage — Scheduling Resolver

Converts an IntentResult into a ResolverDecision.

Design:
  - Data-driven: rules are dicts, not scattered if/else
  - Adding a new event type = 1 entry in EVENT_REQUIREMENTS + 1 Rule
  - Rules are evaluated in priority order; first match wins
  - Never maps 1 intent rigidly to 1 event type — business rules layer decides
"""

from dataclasses import dataclass, field
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Event requirements registry ────────────────────────────────────────────────
#
# Defines what information is required vs optional per event type.
# This is the single source of truth for field requirements.
# title_template uses {customer_name}, {location}, etc. as placeholders.

EVENT_REQUIREMENTS: dict[str, dict] = {
    "site_visit": {
        "required":         ["location"],
        "optional":         ["property_id", "agent_name", "scheduled_for"],
        "title_template":   "Site Visit — {location}",
        "default_title":    "Site Visit",
        "default_priority": "high",
        "default_duration": 90,
    },
    "meeting": {
        "required":         ["scheduled_for"],
        "optional":         ["meeting_type", "meeting_link", "duration_minutes", "agenda"],
        "title_template":   "Meeting with {customer_name}",
        "default_title":    "Meeting",
        "default_priority": "medium",
        "default_duration": 30,
    },
    "callback": {
        "required":         ["preferred_time"],
        "optional":         ["phone", "reason"],
        "title_template":   "Callback — {customer_name}",
        "default_title":    "Callback",
        "default_priority": "high",
        "default_duration": 15,
    },
    "followup": {
        "required":         [],          # follow-ups can be created immediately
        "optional":         ["scheduled_for", "follow_up_reason"],
        "title_template":   "Follow-up — {customer_name}",
        "default_title":    "Follow-up",
        "default_priority": "medium",
        "default_duration": 0,
    },
    "reminder": {
        "required":         ["reminder_message", "scheduled_for"],
        "optional":         ["channel"],
        "title_template":   "Reminder — {reminder_message}",
        "default_title":    "Reminder",
        "default_priority": "low",
        "default_duration": 0,
    },
    "task": {
        "required":         ["task_description"],
        "optional":         ["scheduled_for", "department"],
        "title_template":   "Task — {task_description}",
        "default_title":    "Task",
        "default_priority": "medium",
        "default_duration": 0,
    },
}


# ── Resolver rules ─────────────────────────────────────────────────────────────
#
# Each rule maps (next_action, optional buying_stage, optional urgency)
# to a suggested event_type.
# Rules are evaluated in order — first match wins.
# Add new rules here without touching any other file.

@dataclass
class ResolverRule:
    """A single resolver rule — conditions + output event type."""
    suggested_event_type: str
    next_action:          Optional[str] = None   # match next_action exactly (case-insensitive)
    buying_stage:         Optional[str] = None   # match buying_stage (optional)
    urgency:              Optional[str] = None   # match urgency level (optional)
    min_confidence:       float         = 0.0    # minimum intent confidence to trigger

    def matches(
        self,
        next_action:   Optional[str],
        buying_stage:  Optional[str],
        urgency:       Optional[str],
        confidence:    float,
    ) -> bool:
        """Return True if this rule matches the given intent signals."""
        if confidence < self.min_confidence:
            return False
        if self.next_action and (
            not next_action or
            next_action.lower() != self.next_action.lower()
        ):
            return False
        if self.buying_stage and buying_stage != self.buying_stage:
            return False
        if self.urgency and urgency != self.urgency:
            return False
        return True


# Ordered list — first match wins
INTENT_RESOLVER_RULES: list[ResolverRule] = [
    ResolverRule(
        next_action="Schedule Site Visit",
        suggested_event_type="site_visit",
        min_confidence=0.5,
    ),
    ResolverRule(
        next_action="Confirm Appointment",
        suggested_event_type="meeting",
        min_confidence=0.5,
    ),
    ResolverRule(
        next_action="Create Follow-up",
        buying_stage="Research",
        suggested_event_type="reminder",
        min_confidence=0.4,
    ),
    ResolverRule(
        next_action="Create Follow-up",
        suggested_event_type="followup",
        min_confidence=0.4,
    ),
    ResolverRule(
        next_action="Notify Sales Team",
        urgency="high",
        suggested_event_type="task",
        min_confidence=0.6,
    ),
    ResolverRule(
        next_action="Notify Sales Team",
        suggested_event_type="task",
        min_confidence=0.5,
    ),
    # Add new rules here — no other file changes needed
]


# ── Resolver decision ──────────────────────────────────────────────────────────

@dataclass
class ResolverDecision:
    """
    Output of SchedulingResolver.resolve().

    can_create_immediately=True means all required fields are present
    and a ScheduledEvent can be created right now.

    can_create_immediately=False means missing_fields must be collected
    first via a SchedulingCandidate.
    """
    suggested_event_type:     str
    suggested_title:          str
    required_fields:          list[str]
    optional_fields:          list[str]
    collected_fields:         dict
    missing_fields:           list[str]
    can_create_immediately:   bool
    confidence:               float
    default_priority:         str = "medium"
    default_duration_minutes: int = 30


# ── Resolver class ─────────────────────────────────────────────────────────────

class SchedulingResolver:
    """
    Converts an IntentResult into a ResolverDecision.

    The resolver is stateless — no DB access. It applies business rules
    from INTENT_RESOLVER_RULES and looks up requirements from EVENT_REQUIREMENTS.
    """

    def resolve(
        self,
        next_action:    Optional[str],
        buying_stage:   Optional[str],
        urgency:        Optional[str],
        confidence:     float,
        customer_name:  Optional[str] = None,
        extracted_data: Optional[dict] = None,
    ) -> Optional[ResolverDecision]:
        """
        Apply resolver rules and return a scheduling decision.

        Returns None if no rule matches (intent does not warrant scheduling).

        Args:
            next_action:    The next_action string from IntentResult.
            buying_stage:   Customer's buying stage.
            urgency:        Urgency level string.
            confidence:     Intent confidence score (0.0–1.0).
            customer_name:  For title template rendering.
            extracted_data: Fields already extracted by intent engine
                            (budget, timeline, location, etc.).
        """
        # Find the first matching rule
        matched_rule = None
        for rule in INTENT_RESOLVER_RULES:
            if rule.matches(next_action, buying_stage, urgency, confidence):
                matched_rule = rule
                break

        if matched_rule is None:
            logger.debug(
                "resolver_no_match",
                next_action=next_action,
                buying_stage=buying_stage,
                urgency=urgency,
            )
            return None

        event_type = matched_rule.suggested_event_type
        reqs       = EVENT_REQUIREMENTS.get(event_type, {})
        required   = reqs.get("required", [])
        optional   = reqs.get("optional", [])

        # Pre-populate collected fields from extracted data
        collected = {}
        extracted = extracted_data or {}
        for field_name in required + optional:
            if field_name in extracted and extracted[field_name]:
                collected[field_name] = extracted[field_name]

        # Special mapping: "location" from intent → location metadata field
        if "location" in extracted and extracted.get("location"):
            collected["location"] = extracted["location"]

        missing    = [f for f in required if f not in collected]
        can_create = len(missing) == 0

        # Build title from template
        name         = customer_name or "Customer"
        location     = collected.get("location", "")
        task_desc    = collected.get("task_description", "")
        reminder_msg = collected.get("reminder_message", "")

        title_template = reqs.get("title_template", reqs.get("default_title", event_type.title()))
        try:
            title = title_template.format(
                customer_name=name,
                location=location or "TBD",
                task_description=task_desc or "Follow up",
                reminder_message=reminder_msg or "Reminder",
            )
        except KeyError:
            title = reqs.get("default_title", event_type.title())

        logger.info(
            "resolver_match",
            next_action=next_action,
            event_type=event_type,
            can_create_immediately=can_create,
            missing_fields=missing,
        )

        return ResolverDecision(
            suggested_event_type=event_type,
            suggested_title=title,
            required_fields=required,
            optional_fields=optional,
            collected_fields=collected,
            missing_fields=missing,
            can_create_immediately=can_create,
            confidence=confidence,
            default_priority=reqs.get("default_priority", "medium"),
            default_duration_minutes=reqs.get("default_duration", 30),
        )


# ── Module-level singleton ─────────────────────────────────────────────────────

scheduling_resolver = SchedulingResolver()
