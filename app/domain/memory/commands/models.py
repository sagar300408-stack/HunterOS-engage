"""
HunterOS Engage — Memory Domain Command Objects

Defines strongly-typed Command objects representing state-changing operations
on the CustomerMemory Aggregate Root.
"""

from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.memory.models import LifecycleStatus


class BaseMemoryCommand(BaseModel):
    """Base class for all memory mutation commands."""
    customer_id: UUID
    workspace_id: Optional[UUID] = None
    actor: Optional[str] = "system"
    idempotency_key: Optional[str] = None


class CreateMemoryCommand(BaseMemoryCommand):
    """Command to initialize a new customer memory aggregate."""
    memory_payload: Dict[str, Any] = Field(default_factory=dict)
    source: str = "API"
    created_by: Optional[str] = None


class UpdateMemoryCommand(BaseMemoryCommand):
    """Command to execute a partial update (PATCH) on customer memory."""
    memory_payload: Dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = "Customer profile update"
    trigger: str = "manual_update"
    changed_module: str = "API"
    expected_revision_id: Optional[str] = None
    expected_version: Optional[int] = None


class ReplaceMemoryCommand(BaseMemoryCommand):
    """Command to execute a complete replacement (PUT) of customer memory."""
    memory_payload: Dict[str, Any]
    reason: Optional[str] = "Customer profile full replacement"
    trigger: str = "manual_replacement"
    changed_module: str = "API"
    expected_revision_id: Optional[str] = None
    expected_version: Optional[int] = None


class DeleteMemoryCommand(BaseMemoryCommand):
    """Command to soft-delete customer memory."""
    reason: Optional[str] = "Customer memory soft-deleted"


class RestoreMemoryCommand(BaseMemoryCommand):
    """Command to restore soft-deleted customer memory."""
    reason: Optional[str] = "Customer memory restored"


class ChangeStatusCommand(BaseMemoryCommand):
    """Command to transition customer memory lifecycle status."""
    target_status: LifecycleStatus
    reason: Optional[str] = None


class LockMemoryCommand(BaseMemoryCommand):
    """Command to administratively lock customer memory."""
    reason: Optional[str] = "Administrative lock"


class UnlockMemoryCommand(BaseMemoryCommand):
    """Command to unlock customer memory."""
    reason: Optional[str] = "Administrative unlock"


class ArchiveMemoryCommand(BaseMemoryCommand):
    """Command to archive customer memory."""
    reason: Optional[str] = "Archival lifecycle transition"
