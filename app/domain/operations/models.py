import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.domain.conversations.models import Base


class ActionType(str, enum.Enum):
    CREATE_FOLLOWUP = "CREATE_FOLLOWUP"
    SEND_MESSAGE = "SEND_MESSAGE"
    SCHEDULE_SITE_VISIT = "SCHEDULE_SITE_VISIT"
    CREATE_TASK = "CREATE_TASK"
    UPDATE_CUSTOMER = "UPDATE_CUSTOMER"


class ActionStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    PLANNED = "PLANNED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    READY = "READY"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class ActionPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionDependency(Base):
    """
    Association table tracking action dependencies.
    An action can depend on another action completing before it is ready.
    """
    __tablename__ = "action_dependencies"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    action_id = Column(
        UUID(as_uuid=True),
        ForeignKey("actions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depends_on_action_id = Column(
        UUID(as_uuid=True),
        ForeignKey("actions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint(
            "action_id != depends_on_action_id",
            name="check_no_self_dependency"
        ),
    )


class Action(Base):
    """
    Aggregate Root for domain operations (Actions).
    """
    __tablename__ = "actions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    workspace_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    action_type = Column(
        Enum(ActionType, name="action_type_enum"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(ActionStatus, name="action_status_enum"),
        nullable=False,
        default=ActionStatus.DETECTED,
        index=True,
    )
    priority = Column(
        Enum(ActionPriority, name="action_priority_enum"),
        nullable=False,
        default=ActionPriority.NORMAL,
        index=True,
    )

    # JSONB Fields
    target = Column(JSONB, nullable=False, default=dict)
    owner = Column(JSONB, nullable=False, default=dict)
    source = Column(JSONB, nullable=False, default=dict)
    evidence = Column(JSONB, nullable=False, default=list)
    provenance = Column(JSONB, nullable=False, default=dict)
    execution_metadata = Column(JSONB, nullable=False, default=dict)

    # Concurrency and metadata
    idempotency_key = Column(String(128), nullable=True, index=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    revision_id = Column(
        String(64),
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    dependencies = relationship(
        "ActionDependency",
        foreign_keys="[ActionDependency.action_id]",
        cascade="all, delete-orphan",
    )
    dependent_on_me = relationship(
        "ActionDependency",
        foreign_keys="[ActionDependency.depends_on_action_id]",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = uuid.uuid4()
        if getattr(self, "status", None) is None:
            self.status = ActionStatus.DETECTED
        if getattr(self, "priority", None) is None:
            self.priority = ActionPriority.NORMAL
        if getattr(self, "version_number", None) is None:
            self.version_number = 1
        if getattr(self, "revision_id", None) is None:
            self.revision_id = str(uuid.uuid4())
        if getattr(self, "target", None) is None:
            self.target = {}
        if getattr(self, "owner", None) is None:
            self.owner = {}
        if getattr(self, "source", None) is None:
            self.source = {}
        if getattr(self, "evidence", None) is None:
            self.evidence = []
        if getattr(self, "provenance", None) is None:
            self.provenance = {}
        if getattr(self, "execution_metadata", None) is None:
            self.execution_metadata = {}
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(timezone.utc)
        if getattr(self, "updated_at", None) is None:
            self.updated_at = datetime.now(timezone.utc)

    def advance_revision(self) -> None:
        """Generates a fresh revision ID and increments the aggregate version."""
        self.version_number += 1
        self.revision_id = str(uuid.uuid4())
        self.updated_at = datetime.now(timezone.utc)
