"""
HunterOS Engage — Create Memory Command Handler

Orchestrates creation of a new CustomerMemory Aggregate Root.
"""

from typing import Optional
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.audit.service import MemoryAuditService, get_memory_audit_service
from app.domain.memory.commands.models import CreateMemoryCommand
from app.domain.memory.events.models import MemoryCreatedDomainEvent, NIL_UUID
from app.domain.memory.models import CustomerMemory, LifecycleStatus
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


class CreateMemoryHandler:
    """Handles CreateMemoryCommand within transactional Unit of Work."""

    def __init__(
        self,
        write_repo: Optional[AbstractMemoryWriteRepository] = None,
        validator_pipeline: Optional[MemoryValidationPipeline] = None,
        audit_service: Optional[MemoryAuditService] = None,
        idempotency_manager: Optional[IdempotencyManager] = None,
    ):
        self.write_repo = write_repo or SqlAlchemyMemoryWriteRepository()
        self.validator_pipeline = validator_pipeline or get_validation_pipeline()
        self.audit_service = audit_service or get_memory_audit_service()
        self.idempotency_manager = idempotency_manager or get_idempotency_manager()

    async def handle(
        self,
        session: AsyncSession,
        command: CreateMemoryCommand,
        uow: Optional[MemoryUnitOfWork] = None,
    ) -> CustomerMemory:
        # 1. 5-Stage Validation Pipeline
        context = ValidationContext(
            customer_id=command.customer_id,
            workspace_id=command.workspace_id,
            command_type="create",
            payload=command.memory_payload,
            actor=command.actor,
            session=session,
        )
        await self.validator_pipeline.validate(context)

        # 2. Instantiate Aggregate Root
        memory = CustomerMemory(
            id=uuid4(),
            customer_id=command.customer_id,
            workspace_id=command.workspace_id,
            memory_payload=command.memory_payload or {},
            version_number=1,
            lifecycle_status=LifecycleStatus.ACTIVE,
            is_deleted=False,
        )

        # 3. Persist through Write Repository
        await self.write_repo.add(session, memory)
        await session.flush()

        # 4. Generate Append-Only Audit Records (v1 Snapshot, Timeline, ChangeLog)
        await self.audit_service.record_creation_audit(
            session=session,
            memory=memory,
            actor=command.created_by or command.actor,
            source=command.source,
            reason="Initial creation",
        )

        # 5. Enqueue Domain Event
        domain_event = MemoryCreatedDomainEvent(
            aggregate_id=memory.id,
            customer_id=memory.customer_id,
            workspace_id=memory.workspace_id or NIL_UUID,
            tenant_id=memory.workspace_id,
            version=1,
            payload=memory.memory_payload,
        )
        if uow is not None:
            uow.enqueue_event(domain_event)

        return memory
