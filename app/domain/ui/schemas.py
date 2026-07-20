from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
import uuid

class UserPreferenceSchema(BaseModel):
    theme: str
    high_contrast: bool
    reduced_motion: bool
    saved_views: Dict[str, Any]
    model_config = ConfigDict(from_attributes=True)

class NotificationPreferenceSchema(BaseModel):
    notification_type: str
    email_enabled: bool
    push_enabled: bool
    slack_enabled: bool
    in_app_enabled: bool
    model_config = ConfigDict(from_attributes=True)

class WidgetDataSchema(BaseModel):
    widget_key: str
    title: str
    data_payload: Dict[str, Any]

class DashboardPayloadSchema(BaseModel):
    role: str
    widgets: List[WidgetDataSchema]
    
class NavigationNodeSchema(BaseModel):
    id: uuid.UUID
    label: str
    path: str
    icon: Optional[str]
    children: List['NavigationNodeSchema'] = []
    model_config = ConfigDict(from_attributes=True)

class ExplainabilitySchema(BaseModel):
    decision: str
    reasoning: str
    confidence: float
    policy_applied: Optional[str]
    context_used: List[str]
    alternatives: List[str]
    risk_level: str
    
class CommandCenterIntent(BaseModel):
    intent_type: str # SEARCH, NAVIGATE, EXECUTE, CREATE, ASK
    action_payload: Dict[str, Any]
