"""
HunterOS Engage — Update Memory Command Handler (PATCH)

Orchestrates partial updates to CustomerMemory Aggregate Root.
Enforces optimistic concurrency control, deep field merge, and append-only audit trail.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.audit.service import MemoryAuditService, get_memory_audit_service
from app.domain.memory.commands.models import UpdateMemoryCommand
from app.domain.memory.events.models import MemoryUpdatedDomainEvent, NIL_UUID
from app.domain.memory.models import CustomerMemory, MemoryDomainError
from app.domain.memory.repositories.read_repository import (
    AbstractMemoryReadRepository,
    SqlAlchemyMemoryReadRepository,
)
from app.domain.memory.repositories.write_repository import (
    AbstractMemoryWriteRepository,
    SqlAlchemyMemoryWriteRepository,
)
from app.domain.memory.transactions.idempotency import (
    IdempotencyManager,
    get_idempotency_manager,
)
from app.domain.memory.transactions.unit_of_work import MemoryUnitOfWork
from app.domain.memory.validators.base import ValidationContext
from app.domain.memory.validators.pipeline import (
    MemoryValidationPipeline,
    get_validation_pipeline,
)


class UpdateMemoryHandler:
    """Handles UpdateMemoryCommand (PATCH) within transactional Unit of Work."""

    def __init__(
        self,
        read_repo: Optional[AbstractMemoryReadRepository] = None,
        write_repo: Optional[AbstractMemoryWriteRepository] = None,
        validator_pipeline: Optional[MemoryValidationPipeline] = None,
        audit_service: Optional[MemoryAuditService] = None,
        idempotency_manager: Optional[IdempotencyManager] = None,
    ):
        self.read_repo = read_repo or SqlAlchemyMemoryReadRepository()
        self.write_repo = write_repo or SqlAlchemyMemoryWriteRepository()
        self.validator_pipeline = validator_pipeline or get_validation_pipeline()
        self.audit_service = audit_service or get_memory_audit_service()
        self.idempotency_manager = idempotency_manager or get_idempotency_manager()

    async def handle(
        self,
        session: AsyncSession,
        command: UpdateMemoryCommand,
        uow: Optional[MemoryUnitOfWork] = None,
    ) -> CustomerMemory:
        # 1. Fetch Aggregate
        memory = await self.read_repo.get_by_customer_id(
            session, command.customer_id, include_deleted=True
        )
        if not memory:
            raise MemoryDomainError(f"CustomerMemory for customer {command.customer_id} does not exist.")

        old_version = memory.version_number

        # 2. 5-Stage Validation Pipeline
        context = ValidationContext(
            customer_id=command.customer_id,
            workspace_id=command.workspace_id or memory.workspace_id,
            command_type="update",
            payload=command.memory_payload,
            actor=command.actor,
            existing_memory=memory,
            session=session,
        )
        await self.validator_pipeline.validate(context)

        # 3. Mutate Aggregate State via Domain Method (with OCC check)
        old_payload = memory.update_payload(
            delta_payload=command.memory_payload or {},
            source=command.changed_module,
            actor=command.actor,
            reason=command.reason,
            expected_revision_id=command.expected_revision_id,
            expected_version=command.expected_version,
        )

        # 4. Persist via Write Repo
        await self.write_repo.update(session, memory)
        await session.flush()

        # 5. Append-Only Audit Logging (Snapshot, ChangeLog, Categorized Timeline)
        await self.audit_service.record_update_audit(
            session=session,
            memory=memory,
            old_payload=old_payload,
            new_payload=memory.memory_payload,
            actor=command.actor,
            changed_module=command.changed_module,
            trigger=command.trigger,
            reason=command.reason,
        )

        # 6. Enqueue Domain Event
        domain_event = MemoryUpdatedDomainEvent(
            aggregate_id=memory.id,
            customer_id=memory.customer_id,
            workspace_id=memory.workspace_id or NIL_UUID,
            tenant_id=memory.workspace_id,
            version=memory.version_number,
            old_version=old_version,
            new_version=memory.version_number,
            changed_fields=list((command.memory_payload or {}).keys()),
            payload=memory.memory_payload,
        )
        if uow is not None:
            uow.enqueue_event(domain_event)

        return memory
