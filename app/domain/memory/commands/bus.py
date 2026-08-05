"""
HunterOS Engage — Memory Command Bus

Dispatches state-changing command objects to specialized command handlers
within transactional MemoryUnitOfWork boundaries with idempotency management.
"""

import copy
import logging
from typing import Any, Dict, Optional, Type, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.commands.change_status import ChangeStatusHandler
from app.domain.memory.commands.create_memory import CreateMemoryHandler
from app.domain.memory.commands.delete_memory import DeleteMemoryHandler
from app.domain.memory.commands.models import (
    ArchiveMemoryCommand,
    BaseMemoryCommand,
    ChangeStatusCommand,
    CreateMemoryCommand,
    DeleteMemoryCommand,
    LockMemoryCommand,
    ReplaceMemoryCommand,
    RestoreMemoryCommand,
    UnlockMemoryCommand,
    UpdateMemoryCommand,
)
from app.domain.memory.commands.replace_memory import ReplaceMemoryHandler
from app.domain.memory.commands.restore_memory import RestoreMemoryHandler
from app.domain.memory.commands.update_memory import UpdateMemoryHandler
from app.domain.memory.events.publisher import (
    AbstractMemoryEventPublisher,
    get_memory_event_publisher,
)
from app.domain.memory.models import CustomerMemory, LifecycleStatus
from app.domain.memory.transactions.idempotency import (
    IdempotencyManager,
    get_idempotency_manager,
)
from app.domain.memory.transactions.unit_of_work import MemoryUnitOfWork

logger = logging.getLogger(__name__)


class MemoryCommandBus:
    """
    CQRS Command Bus dispatching memory domain commands to isolated handlers.
    """

    def __init__(
        self,
        create_handler: Optional[CreateMemoryHandler] = None,
        update_handler: Optional[UpdateMemoryHandler] = None,
        replace_handler: Optional[ReplaceMemoryHandler] = None,
        delete_handler: Optional[DeleteMemoryHandler] = None,
        restore_handler: Optional[RestoreMemoryHandler] = None,
        change_status_handler: Optional[ChangeStatusHandler] = None,
        event_publisher: Optional[AbstractMemoryEventPublisher] = None,
        idempotency_manager: Optional[IdempotencyManager] = None,
    ):
        self.create_handler = create_handler or CreateMemoryHandler()
        self.update_handler = update_handler or UpdateMemoryHandler()
        self.replace_handler = replace_handler or ReplaceMemoryHandler()
        self.delete_handler = delete_handler or DeleteMemoryHandler()
        self.restore_handler = restore_handler or RestoreMemoryHandler()
        self.change_status_handler = change_status_handler or ChangeStatusHandler()
        self.event_publisher = event_publisher or get_memory_event_publisher()
        self.idempotency_manager = idempotency_manager or get_idempotency_manager()

    async def execute(
        self,
        session: AsyncSession,
        command: BaseMemoryCommand,
    ) -> Union[CustomerMemory, Dict[str, Any]]:
        """
        Executes a command within a transactional Unit of Work.
        Guarantees idempotency checking and atomic commit/rollback.
        """
        idempotency_key = command.idempotency_key
        request_hash = None

        if idempotency_key:
            request_hash = self.idempotency_manager.compute_request_hash(command.model_dump())
            cached = await self.idempotency_manager.get_cached_response(
                session, idempotency_key, request_hash
            )
            if cached is not None:
                status_code, body = cached
                return body

        # Execute inside transactional Unit of Work
        async with MemoryUnitOfWork(session=session, event_publisher=self.event_publisher) as uow:
            result_memory = await self._dispatch(session, command, uow)

            # If idempotency key provided, store response before committing UoW
            if idempotency_key and request_hash and result_memory:
                cached_body = {
                    "id": str(result_memory.id),
                    "customer_id": str(result_memory.customer_id),
                    "workspace_id": str(result_memory.workspace_id) if result_memory.workspace_id else None,
                    "version_number": result_memory.version_number,
                    "revision_id": result_memory.revision_id,
                    "lifecycle_status": result_memory.lifecycle_status.value,
                    "is_deleted": result_memory.is_deleted,
                    "memory_payload": result_memory.memory_payload,
                    "created_at": result_memory.created_at.isoformat(),
                    "updated_at": result_memory.updated_at.isoformat(),
                }
                await self.idempotency_manager.save_response(
                    session=session,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_status=200,
                    response_body=cached_body,
                )

            await uow.commit()

        return result_memory

    async def _dispatch(
        self,
        session: AsyncSession,
        command: BaseMemoryCommand,
        uow: MemoryUnitOfWork,
    ) -> CustomerMemory:
        """Routes command to appropriate handler."""
        if isinstance(command, CreateMemoryCommand):
            return await self.create_handler.handle(session, command, uow)
        elif isinstance(command, UpdateMemoryCommand):
            return await self.update_handler.handle(session, command, uow)
        elif isinstance(command, ReplaceMemoryCommand):
            return await self.replace_handler.handle(session, command, uow)
        elif isinstance(command, DeleteMemoryCommand):
            return await self.delete_handler.handle(session, command, uow)
        elif isinstance(command, RestoreMemoryCommand):
            return await self.restore_handler.handle(session, command, uow)
        elif isinstance(command, ChangeStatusCommand):
            return await self.change_status_handler.handle(session, command, uow)
        elif isinstance(command, LockMemoryCommand):
            status_cmd = ChangeStatusCommand(
                customer_id=command.customer_id,
                workspace_id=command.workspace_id,
                actor=command.actor,
                target_status=LifecycleStatus.LOCKED,
                reason=command.reason,
            )
            return await self.change_status_handler.handle(session, status_cmd, uow)
        elif isinstance(command, UnlockMemoryCommand):
            status_cmd = ChangeStatusCommand(
                customer_id=command.customer_id,
                workspace_id=command.workspace_id,
                actor=command.actor,
                target_status=LifecycleStatus.ACTIVE,
                reason=command.reason,
            )
            return await self.change_status_handler.handle(session, status_cmd, uow)
        elif isinstance(command, ArchiveMemoryCommand):
            status_cmd = ChangeStatusCommand(
                customer_id=command.customer_id,
                workspace_id=command.workspace_id,
                actor=command.actor,
                target_status=LifecycleStatus.ARCHIVED,
                reason=command.reason,
            )
            return await self.change_status_handler.handle(session, status_cmd, uow)
        else:
            raise TypeError(f"Unsupported command type: {type(command)}")


# Default CommandBus singleton
_default_command_bus: Optional[MemoryCommandBus] = None


def get_memory_command_bus() -> MemoryCommandBus:
    global _default_command_bus
    if _default_command_bus is None:
        _default_command_bus = MemoryCommandBus()
    return _default_command_bus
