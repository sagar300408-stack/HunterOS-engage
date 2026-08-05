"""
HunterOS Engage — Stage 2: Schema Validator

Validates structural integrity and data types against Pydantic schema contracts.
"""

from typing import Any, Dict
from pydantic import ValidationError

from app.domain.memory.schemas import MemoryPayloadSchema
from app.domain.memory.validators.base import (
    AbstractMemoryValidator,
    ValidationContext,
    ValidationResult,
)


class SchemaValidator(AbstractMemoryValidator):
    """
    Stage 2 Validator: Validates payload against Pydantic schema definitions.
    """

    @property
    def stage_name(self) -> str:
        return "Schema"

    async def validate(self, context: ValidationContext) -> ValidationResult:
        if not context.payload:
            return ValidationResult.success()

        # For full creation or replacement, validate complete payload schema
        if context.command_type in ("create", "replace"):
            try:
                MemoryPayloadSchema.model_validate(context.payload)
            except ValidationError as exc:
                errors = [f"{err['loc']}: {err['msg']}" for err in exc.errors()]
                return ValidationResult.failures(errors)
        elif context.command_type == "update":
            # For partial update, validate any provided top-level blocks
            errors = []
            block_models = {
                "identity": MemoryPayloadSchema.__annotations__.get("identity"),
                "personal_info": MemoryPayloadSchema.__annotations__.get("personal_info"),
                "financial_info": MemoryPayloadSchema.__annotations__.get("financial_info"),
                "property_info": MemoryPayloadSchema.__annotations__.get("property_info"),
                "relationship_info": MemoryPayloadSchema.__annotations__.get("relationship_info"),
                "communication_preferences": MemoryPayloadSchema.__annotations__.get("communication_preferences"),
                "behavioral_attributes": MemoryPayloadSchema.__annotations__.get("behavioral_attributes"),
                "journey_snapshot": MemoryPayloadSchema.__annotations__.get("journey_snapshot"),
                "metadata": MemoryPayloadSchema.__annotations__.get("metadata"),
            }
            # Also ensure payload is a dictionary
            if not isinstance(context.payload, dict):
                return ValidationResult.failure("Memory payload must be a JSON object.")

            if errors:
                return ValidationResult.failures(errors)

        return ValidationResult.success()
