"""
HunterOS Engage — Change Status Command Handler

Orchestrates lifecycle status transitions (LOCKED, ARCHIVED, ACTIVE, etc.)
on the CustomerMemory Aggregate Root.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.audit.service import MemoryAuditService, get_memory_audit_service
from app.domain.memory.commands.models import ChangeStatusCommand
from app.domain.memory.events.models import MemoryStatusChangedDomainEvent, NIL_UUID
from app.domain.memory.models import CustomerMemory, MemoryDomainError
from app.domain.memory.repositories.read_repository import (
    AbstractMemoryReadRepository,
    SqlAlchemyMemoryReadRepository,
)
from app.domain.memory.repositories.write_repository import (
    AbstractMemoryWriteRepository,
    SqlAlchemyMemoryWriteRepository,
)
from app.domain.memory.transactions.unit_of_work import MemoryUnitOfWork
from app.domain.memory.validators.base import ValidationContext
from app.domain.memory.validators.pipeline import (
    MemoryValidationPipeline,
    get_validation_pipeline,
)


class ChangeStatusHandler:
    """Handles ChangeStatusCommand within transactional Unit of Work."""

    def __init__(
        self,
        read_repo: Optional[AbstractMemoryReadRepository] = None,
        write_repo: Optional[AbstractMemoryWriteRepository] = None,
        validator_pipeline: Optional[MemoryValidationPipeline] = None,
        audit_service: Optional[MemoryAuditService] = None,
    ):
        self.read_repo = read_repo or SqlAlchemyMemoryReadRepository()
        self.write_repo = write_repo or SqlAlchemyMemoryWriteRepository()
        self.validator_pipeline = validator_pipeline or get_validation_pipeline()
        self.audit_service = audit_service or get_memory_audit_service()

    async def handle(
        self,
        session: AsyncSession,
        command: ChangeStatusCommand,
        uow: Optional[MemoryUnitOfWork] = None,
    ) -> CustomerMemory:
        # 1. Fetch Aggregate
        memory = await self.read_repo.get_by_customer_id(
            session, command.customer_id, include_deleted=True
        )
        if not memory:
            raise MemoryDomainError(f"CustomerMemory for customer {command.customer_id} does not exist.")

        old_status = memory.lifecycle_status

        # 2. 5-Stage Validation Pipeline
        context = ValidationContext(
            customer_id=command.customer_id,
            workspace_id=command.workspace_id or memory.workspace_id,
            command_type="status_change",
            actor=command.actor,
            existing_memory=memory,
            session=session,
        )
        await self.validator_pipeline.validate(context)

        # 3. Mutate Aggregate via Domain Method
        memory.transition_status(
            target_status=command.target_status,
            reason=command.reason,
            actor=command.actor,
        )

        # 4. Persist via Write Repo
        await self.write_repo.update(session, memory)
        await session.flush()

        # 5. Append-Only Audit Logging
        await self.audit_service.record_status_transition_audit(
            session=session,
            memory=memory,
            old_status=old_status,
            new_status=command.target_status,
            actor=command.actor,
            reason=command.reason,
        )

        # 6. Enqueue Domain Event
        domain_event = MemoryStatusChangedDomainEvent(
            aggregate_id=memory.id,
            customer_id=memory.customer_id,
            workspace_id=memory.workspace_id or NIL_UUID,
            tenant_id=memory.workspace_id,
            version=memory.version_number,
            previous_status=old_status.value,
            current_status=command.target_status.value,
            reason=command.reason,
        )
        if uow is not None:
            uow.enqueue_event(domain_event)

        return memory
