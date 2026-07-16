import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class KpiCategory(str, enum.Enum):
    SALES = "sales"
    CUSTOMER = "customer"
    AUTOMATION = "automation"
    OPERATIONAL = "operational"
    EXECUTIVE = "executive"


class KpiUnit(str, enum.Enum):
    PERCENTAGE = "percentage"
    COUNT = "count"
    TIME = "time"
    SCORE = "score"
    CURRENCY = "currency"


class KpiDirection(str, enum.Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class KpiTrend(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class KpiStatus(str, enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class KpiSnapshot(Base):
    """
    Read model for KPI Intelligence Engine.
    Treats KPIs as first-class intelligence objects with rich metadata.
    """
    __tablename__ = "kpi_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Target entity
    target_type = Column(String(50), nullable=False, index=True)  # workspace, customer, conversation
    target_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Core Definition
    kpi_name = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)
    unit = Column(String(50), nullable=False)
    direction = Column(String(50), nullable=False)
    
    # Values
    current_value = Column(Float, nullable=False)
    previous_value = Column(Float, nullable=True)
    percentage_change = Column(Float, nullable=True)
    
    # Interpretations
    trend = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    
    # Thresholds
    target = Column(Float, nullable=True)
    warning_threshold = Column(Float, nullable=True)
    critical_threshold = Column(Float, nullable=True)
    
    # Metadata
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    data_source = Column(String(100), nullable=False)
    refresh_strategy = Column(String(50), nullable=False)
    
    # Timestamps
    calculated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
