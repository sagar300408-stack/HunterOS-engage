"""
HunterOS Engage — Stage 4: Business Rule Validator

Validates lifecycle business rules and status protection invariants.
"""

from app.domain.memory.models import LifecycleStatus
from app.domain.memory.validators.base import (
    AbstractMemoryValidator,
    ValidationContext,
    ValidationResult,
)


class BusinessRuleValidator(AbstractMemoryValidator):
    """
    Stage 4 Validator: Enforces business lifecycle constraints.
    """

    @property
    def stage_name(self) -> str:
        return "BusinessRule"

    async def validate(self, context: ValidationContext) -> ValidationResult:
        memory = context.existing_memory
        if not memory:
            return ValidationResult.success()

        errors = []

        # Mutations on locked/archived/migrating memories are forbidden
        if context.command_type in ("update", "replace", "delete"):
            if memory.lifecycle_status == LifecycleStatus.LOCKED:
                errors.append(f"CustomerMemory {context.customer_id} is LOCKED. Modifications are forbidden.")
            elif memory.lifecycle_status == LifecycleStatus.ARCHIVED:
                errors.append(f"CustomerMemory {context.customer_id} is ARCHIVED. Record is read-only.")
            elif memory.lifecycle_status == LifecycleStatus.MIGRATING:
                errors.append(f"CustomerMemory {context.customer_id} is currently MIGRATING. Writes are temporarily blocked.")

        # Soft-deleted record cannot be updated without prior restoration
        if context.command_type in ("update", "replace"):
            if memory.is_deleted or memory.lifecycle_status == LifecycleStatus.SOFT_DELETED:
                errors.append(f"CustomerMemory {context.customer_id} is soft-deleted. Restore the memory before updating.")

        if errors:
            return ValidationResult.failures(errors)
        return ValidationResult.success()
