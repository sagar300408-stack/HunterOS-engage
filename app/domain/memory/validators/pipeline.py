"""
HunterOS Engage — 5-Stage Memory Validation Pipeline

Executes the sequential 5-stage validation pipeline:
  Stage 1: Authorization
  Stage 2: Schema
  Stage 3: Domain
  Stage 4: Business Rule
  Stage 5: Persistence
"""

import logging
from typing import List, Optional

from app.domain.memory.validators.authorization_validator import AuthorizationValidator
from app.domain.memory.validators.base import (
    AbstractMemoryValidator,
    MemoryValidationError,
    ValidationContext,
    ValidationResult,
)
from app.domain.memory.validators.business_rule_validator import BusinessRuleValidator
from app.domain.memory.validators.domain_validator import DomainValidator
from app.domain.memory.validators.persistence_validator import PersistenceValidator
from app.domain.memory.validators.schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


class MemoryValidationPipeline:
    """
    Coordinates and runs the 5-stage validation pipeline in deterministic sequence.
    """

    def __init__(self, validators: Optional[List[AbstractMemoryValidator]] = None):
        if validators is not None:
            self._validators = validators
        else:
            self._validators = [
                AuthorizationValidator(),
                SchemaValidator(),
                DomainValidator(),
                BusinessRuleValidator(),
                PersistenceValidator(),
            ]

    async def validate(self, context: ValidationContext) -> None:
        """
        Executes each validation stage in order.
        Raises MemoryValidationError immediately if any stage fails.
        """
        for validator in self._validators:
            result: ValidationResult = await validator.validate(context)
            if not result.is_valid:
                logger.warning(
                    f"Memory validation failed at stage {validator.stage_name}",
                    extra={
                        "stage": validator.stage_name,
                        "customer_id": str(context.customer_id),
                        "errors": result.errors,
                    },
                )
                raise MemoryValidationError(stage=validator.stage_name, errors=result.errors)


# Default pipeline instance
_default_pipeline: Optional[MemoryValidationPipeline] = None


def get_validation_pipeline() -> MemoryValidationPipeline:
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = MemoryValidationPipeline()
    return _default_pipeline
