import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Float, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base

class UserPreference(Base):
    __tablename__ = "ui_user_preferences"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    theme = Column(String, default="system")
    high_contrast = Column(Boolean, default=False)
    reduced_motion = Column(Boolean, default=False)
    saved_views = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class NotificationPreference(Base):
    __tablename__ = "ui_notification_preferences"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    notification_type = Column(String, nullable=False) # e.g., "Critical Approval"
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    slack_enabled = Column(Boolean, default=False)
    in_app_enabled = Column(Boolean, default=True)

class DashboardDefinition(Base):
    __tablename__ = "ui_dashboard_definitions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    role_key = Column(String, nullable=False) # e.g., "executive", "manager", "employee"
    layout_config = Column(JSON, default=list) # Array of widget keys and positions
    filters = Column(JSON, default=dict)
    is_customized = Column(Boolean, default=False)

class NavigationNode(Base):
    __tablename__ = "ui_navigation_nodes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    label = Column(String, nullable=False)
    path = Column(String, nullable=False)
    icon = Column(String, nullable=True)
    required_capability = Column(String, nullable=True) # E.g. "LEAD_INTELLIGENCE"
    parent_id = Column(UUID(as_uuid=True), nullable=True)
    order_index = Column(Integer, default=0)

class FeatureFlag(Base):
    __tablename__ = "ui_feature_flags"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    flag_key = Column(String, nullable=False, unique=True)
    is_enabled = Column(Boolean, default=False)
    description = Column(String, nullable=True)

class UXAnalyticsEvent(Base):
    __tablename__ = "ui_ux_analytics_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String, nullable=False) # e.g., "TIME_TO_APPROVE", "ABANDONED_WORKFLOW"
    duration_ms = Column(Integer, nullable=True)
    metadata_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
