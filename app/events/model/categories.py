from enum import Enum

class EventCategory(str, Enum):
    """
    Standardized event categories across the HunterOS platform.
    Every event must belong to exactly one category.
    """
    CUSTOMER = "CUSTOMER"
    CONVERSATION = "CONVERSATION"
    MEETING = "MEETING"
    SCHEDULING = "SCHEDULING"
    FOLLOWUP = "FOLLOWUP"
    CRM = "CRM"
    AUTOMATION = "AUTOMATION"
    RESEARCH = "RESEARCH"
    PROPOSAL = "PROPOSAL"
    ANALYTICS = "ANALYTICS"
    AUDIT = "AUDIT"
    NOTIFICATION = "NOTIFICATION"
    AI_DECISION = "AI_DECISION"
    PLATFORM = "PLATFORM"
    ACTION = "ACTION"
    APPROVAL = "APPROVAL"
    MARKETPLACE = "MARKETPLACE"
    INTEGRATION = "INTEGRATION"
    AUTONOMOUS = "AUTONOMOUS"
    FRICTION = "FRICTION"
    LEAD = "LEAD"
    SLA = "SLA"
