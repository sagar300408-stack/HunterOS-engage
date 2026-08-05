"""
HunterOS Engage — Validation Pipeline Base Interfaces

Defines the validation context, result structure, and base validator contract
for the 5-stage memory validation pipeline.
"""

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.models import CustomerMemory, MemoryDomainError


class MemoryValidationError(MemoryDomainError):
    """Raised when validation fails at any stage of the pipeline."""

    def __init__(self, stage: str, errors: List[str]):
        self.stage = stage
        self.errors = errors
        message = f"Validation failed at stage '{stage}': " + "; ".join(errors)
        super().__init__(message)


@dataclass
class ValidationContext:
    """Carries execution state through all 5 validation stages."""
    customer_id: UUID
    workspace_id: Optional[UUID] = None
    command_type: str = "unknown"
    payload: Optional[Dict[str, Any]] = None
    actor: Optional[str] = None
    existing_memory: Optional[CustomerMemory] = None
    session: Optional[AsyncSession] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Outcome of a validation stage."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(is_valid=True)

    @classmethod
    def failure(cls, error: str) -> "ValidationResult":
        return cls(is_valid=False, errors=[error])

    @classmethod
    def failures(cls, errors: List[str]) -> "ValidationResult":
        return cls(is_valid=False, errors=errors)


class AbstractMemoryValidator(abc.ABC):
    """Contract for a single stage in the 5-stage validation pipeline."""

    @property
    @abc.abstractmethod
    def stage_name(self) -> str:
        """Name of the validation stage."""
        raise NotImplementedError

    @abc.abstractmethod
    async def validate(self, context: ValidationContext) -> ValidationResult:
        """Executes validation against the supplied context."""
        raise NotImplementedError
