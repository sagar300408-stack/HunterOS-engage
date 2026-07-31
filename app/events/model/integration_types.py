from enum import Enum

class IntegrationType(str, Enum):
    WHATSAPP = "WHATSAPP"
    INSTAGRAM = "INSTAGRAM"
    EMAIL = "EMAIL"
    VOICE = "VOICE"
    CRM = "CRM"
    WEBSITE = "WEBSITE"
    SLACK = "SLACK"
    TEAMS = "TEAMS"
    SYSTEM = "SYSTEM"
