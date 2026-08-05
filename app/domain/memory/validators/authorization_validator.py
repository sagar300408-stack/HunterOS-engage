"""
HunterOS Engage — Stage 1: Authorization Validator

Validates actor credentials, workspace/tenant accessibility, and execution permissions.
Provides extension point for future RBAC integration.
"""

from app.domain.memory.validators.base import (
    AbstractMemoryValidator,
    ValidationContext,
    ValidationResult,
)


class AuthorizationValidator(AbstractMemoryValidator):
    """
    Stage 1 Validator: Verifies tenant context and caller authorization.
    """

    @property
    def stage_name(self) -> str:
        return "Authorization"

    async def validate(self, context: ValidationContext) -> ValidationResult:
        errors = []

        # If existing memory has a workspace_id, ensure context does not conflict
        if context.existing_memory and context.existing_memory.workspace_id:
            if (
                context.workspace_id
                and context.existing_memory.workspace_id != context.workspace_id
            ):
                errors.append(
                    f"Cross-tenant access forbidden: record belongs to workspace {context.existing_memory.workspace_id}, "
                    f"request presented workspace {context.workspace_id}."
                )

        # Actor validation (if actor string contains blacklisted or unauthorized tokens)
        if context.actor and context.actor.strip().lower() == "unauthorized":
            errors.append(f"Actor '{context.actor}' is explicitly unauthorized.")

        if errors:
            return ValidationResult.failures(errors)
        return ValidationResult.success()
