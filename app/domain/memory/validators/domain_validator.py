"""
HunterOS Engage — Stage 3: Domain Validator

Validates domain invariants and business entity consistency rules.
"""

from typing import Any, Dict
from app.domain.memory.validators.base import (
    AbstractMemoryValidator,
    ValidationContext,
    ValidationResult,
)


class DomainValidator(AbstractMemoryValidator):
    """
    Stage 3 Validator: Enforces domain-specific invariants on structured memory blocks.
    """

    @property
    def stage_name(self) -> str:
        return "Domain"

    async def validate(self, context: ValidationContext) -> ValidationResult:
        if not context.payload or not isinstance(context.payload, dict):
            return ValidationResult.success()

        errors = []
        payload = context.payload

        # 1. Financial Invariants
        financial = payload.get("financial_info")
        if isinstance(financial, dict):
            b_min = financial.get("budget_min")
            b_max = financial.get("budget_max")
            if b_min is not None and b_max is not None:
                if isinstance(b_min, (int, float)) and isinstance(b_max, (int, float)):
                    if b_min < 0 or b_max < 0:
                        errors.append("Financial budget cannot be negative.")
                    if b_min > b_max:
                        errors.append(f"budget_min ({b_min}) cannot exceed budget_max ({b_max}).")

        # 2. Communication Preferences Invariants
        comm = payload.get("communication_preferences")
        if isinstance(comm, dict):
            channels = comm.get("preferred_channels")
            if channels is not None and not isinstance(channels, list):
                errors.append("preferred_channels must be a list of channel strings.")

        if errors:
            return ValidationResult.failures(errors)
        return ValidationResult.success()
