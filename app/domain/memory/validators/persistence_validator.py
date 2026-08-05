"""
HunterOS Engage — Stage 5: Persistence Validator

Validates referential integrity, foreign key references, and duplicate record protection.
"""

from sqlalchemy import select
from app.domain.customers.models import Customer
from app.domain.memory.models import CustomerMemory
from app.domain.memory.validators.base import (
    AbstractMemoryValidator,
    ValidationContext,
    ValidationResult,
)


class PersistenceValidator(AbstractMemoryValidator):
    """
    Stage 5 Validator: Verifies database-level referential integrity and uniqueness.
    """

    @property
    def stage_name(self) -> str:
        return "Persistence"

    async def validate(self, context: ValidationContext) -> ValidationResult:
        if not context.session:
            return ValidationResult.success()

        session = context.session
        errors = []

        # 1. Customer existence verification
        cust_stmt = select(Customer).where(Customer.id == context.customer_id)
        cust_res = await session.execute(cust_stmt)
        customer = cust_res.scalar_one_or_none()

        if not customer:
            errors.append(f"Customer with id {context.customer_id} does not exist.")

        # 2. Duplicate protection on creation
        if context.command_type == "create":
            mem_stmt = select(CustomerMemory).where(CustomerMemory.customer_id == context.customer_id)
            mem_res = await session.execute(mem_stmt)
            existing = mem_res.scalar_one_or_none()
            if existing:
                errors.append(f"CustomerMemory already exists for customer {context.customer_id}.")

        if errors:
            return ValidationResult.failures(errors)
        return ValidationResult.success()
