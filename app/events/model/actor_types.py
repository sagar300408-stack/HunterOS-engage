from enum import Enum

class ActorType(str, Enum):
    """
    Standardized actor types across the HunterOS platform.
    Identifies who or what produced an event.
    """
    AI_AGENT = "ai_agent"
    HUMAN_AGENT = "human_agent"
    SYSTEM = "system"
    CUSTOMER = "customer"
    EXTERNAL_INTEGRATION = "external_integration"
