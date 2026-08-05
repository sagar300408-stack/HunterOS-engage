"""
HunterOS Engage — Memory Domain Service Implementation (CQRS Orchestrator)

Orchestrates foundational customer memory operations by routing:
  - State mutations (Commands) -> MemoryCommandBus / Command Handlers
  - Queries (Reads)           -> SqlAlchemyMemoryReadRepository
"""

import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.audit.service import (
    MemoryAuditService,
    compute_memory_diff,
    compute_snapshot_hash,
    deep_merge_dicts,
    get_memory_audit_service,
    map_field_path_to_category,
)
from app.domain.memory.commands.bus import MemoryCommandBus, get_memory_command_bus
from app.domain.memory.commands.models import (
    ArchiveMemoryCommand,
    ChangeStatusCommand,
    CreateMemoryCommand,
    DeleteMemoryCommand,
    LockMemoryCommand,
    ReplaceMemoryCommand,
    RestoreMemoryCommand,
    UnlockMemoryCommand,
    UpdateMemoryCommand,
)
from app.domain.memory.interfaces.read_repository import AbstractMemoryReadRepository
from app.domain.memory.interfaces.service import AbstractMemoryService
from app.domain.memory.models import (
    CustomerMemory,
    CustomerMemoryTimelineEvent,
    CustomerMemoryVersion,
    LifecycleStatus,
    MemoryChangeLog,
    MemoryDomainError,
)
from app.domain.memory.repositories.read_repository import SqlAlchemyMemoryReadRepository
from app.domain.memory.schemas import (
    CustomerMemoryBulkCreateRequest,
    CustomerMemoryBulkGetRequest,
    CustomerMemoryBulkUpdateRequest,
    CustomerMemoryCreateRequest,
    CustomerMemoryHistoryResponse,
    CustomerMemoryReplaceRequest,
    CustomerMemoryResponse,
    CustomerMemorySearchResponse,
    CustomerMemorySearchResultItem,
    CustomerMemoryTimelineEventResponse,
    CustomerMemoryUpdateRequest,
    CustomerMemoryVersionResponse,
    MemoryChangeLogResponse,
    MemoryPayloadSchema,
    MemorySearchRequest,
    MemoryTimelineFilterRequest,
)
from app.domain.memory.graph.facade import KnowledgeGraphFacade
from app.domain.memory.queries.facade import MemoryQueryFacade
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryService(AbstractMemoryService):
    """
    Unified CQRS Orchestrator for Memory Domain.
    """

    def __init__(
        self,
        command_bus: Optional[MemoryCommandBus] = None,
        read_repo: Optional[AbstractMemoryReadRepository] = None,
        audit_service: Optional[MemoryAuditService] = None,
        query_facade: Optional[MemoryQueryFacade] = None,
        knowledge_graph: Optional[KnowledgeGraphFacade] = None,
    ) -> None:
        self._command_bus = command_bus or get_memory_command_bus()
        self._read_repo = read_repo or SqlAlchemyMemoryReadRepository()
        self._audit_service = audit_service or get_memory_audit_service()
        self._query_facade = query_facade or MemoryQueryFacade(self._read_repo)
        self._knowledge_graph = knowledge_graph or KnowledgeGraphFacade()

    @property
    def query_facade(self) -> MemoryQueryFacade:
        """Access underlying Query Facade."""
        return self._query_facade

    @property
    def knowledge_graph(self) -> KnowledgeGraphFacade:
        """Access underlying Business Knowledge Graph Facade."""
        return self._knowledge_graph

    # ── Command Methods (Mutations) ───────────────────────────────────────────

    async def create_customer_memory(
        self, request: CustomerMemoryCreateRequest, session: AsyncSession
    ) -> CustomerMemory:
        """Initialize structured customer memory aggregate."""
        if isinstance(request.memory_payload, MemoryPayloadSchema):
            payload_dict = request.memory_payload.model_dump(mode="json")
        elif isinstance(request.memory_payload, dict):
            payload_dict = request.memory_payload
        else:
            payload_dict = MemoryPayloadSchema().model_dump(mode="json")

        cmd = CreateMemoryCommand(
            customer_id=request.customer_id,
            workspace_id=request.workspace_id,
            memory_payload=payload_dict,
            source=request.source,
            created_by=request.created_by,
            idempotency_key=request.idempotency_key,
        )
        res = await self._command_bus.execute(session, cmd)
        if isinstance(res, dict):
            # Cached response returned from idempotency record
            return await self._read_repo.get_by_customer_id(session, request.customer_id)
        return res

    async def update_customer_memory(
        self,
        customer_id: UUID,
        request: CustomerMemoryUpdateRequest,
        session: AsyncSession,
    ) -> CustomerMemory:
        """Update memory fields with automatic versioning (PATCH)."""
        cmd = UpdateMemoryCommand(
            customer_id=customer_id,
            workspace_id=request.workspace_id,
            memory_payload=request.memory_payload or {},
            reason=request.reason,
            trigger=request.trigger,
            changed_module=request.changed_module,
            actor=request.changed_by or request.changed_module,
            expected_revision_id=request.expected_revision_id,
            expected_version=request.expected_version,
            idempotency_key=request.idempotency_key,
        )
        res = await self._command_bus.execute(session, cmd)
        if isinstance(res, dict):
            return await self._read_repo.get_by_customer_id(session, customer_id)
        return res

    async def replace_customer_memory(
        self,
        customer_id: UUID,
        request: CustomerMemoryReplaceRequest,
        session: AsyncSession,
    ) -> CustomerMemory:
        """Completely replace memory payload (PUT)."""
        payload_dict = (
            request.memory_payload.model_dump(mode="json")
            if isinstance(request.memory_payload, MemoryPayloadSchema)
            else request.memory_payload
        )
        cmd = ReplaceMemoryCommand(
            customer_id=customer_id,
            workspace_id=request.workspace_id,
            memory_payload=payload_dict,
            reason=request.reason,
            trigger=request.trigger,
            changed_module=request.changed_module,
            actor=request.changed_by or request.changed_module,
            expected_revision_id=request.expected_revision_id,
            expected_version=request.expected_version,
            idempotency_key=request.idempotency_key,
        )
        res = await self._command_bus.execute(session, cmd)
        if isinstance(res, dict):
            return await self._read_repo.get_by_customer_id(session, customer_id)
        return res

    async def soft_delete_memory(
        self,
        customer_id: UUID,
        reason: Optional[str] = None,
        changed_by: Optional[str] = None,
        session: AsyncSession = None,
    ) -> CustomerMemory:
        """Soft-delete memory record."""
        cmd = DeleteMemoryCommand(
            customer_id=customer_id,
            reason=reason or "Customer memory soft-deleted",
            actor=changed_by or "API",
        )
        res = await self._command_bus.execute(session, cmd)
        if isinstance(res, dict):
            return await self._read_repo.get_by_customer_id(session, customer_id, include_deleted=True)
        return res

    async def restore_memory(
        self,
        customer_id: UUID,
        changed_by: Optional[str] = None,
        session: AsyncSession = None,
    ) -> CustomerMemory:
        """Restore soft-deleted memory record."""
        cmd = RestoreMemoryCommand(
            customer_id=customer_id,
            reason="Customer memory restored",
            actor=changed_by or "API",
        )
        res = await self._command_bus.execute(session, cmd)
        if isinstance(res, dict):
            return await self._read_repo.get_by_customer_id(session, customer_id)
        return res

    async def change_lifecycle_status(
        self,
        customer_id: UUID,
        target_status: LifecycleStatus,
        reason: Optional[str] = None,
        changed_by: Optional[str] = None,
        session: AsyncSession = None,
    ) -> CustomerMemory:
        """Transition customer memory lifecycle status."""
        cmd = ChangeStatusCommand(
            customer_id=customer_id,
            target_status=target_status,
            reason=reason,
            actor=changed_by or "API",
        )
        res = await self._command_bus.execute(session, cmd)
        if isinstance(res, dict):
            return await self._read_repo.get_by_customer_id(session, customer_id, include_deleted=True)
        return res

    async def lock_memory(
        self,
        customer_id: UUID,
        reason: Optional[str] = "Administrative lock",
        changed_by: Optional[str] = None,
        session: AsyncSession = None,
    ) -> CustomerMemory:
        """Lock customer memory."""
        cmd = LockMemoryCommand(
            customer_id=customer_id,
            reason=reason,
            actor=changed_by or "API",
        )
        res = await self._command_bus.execute(session, cmd)
        if isinstance(res, dict):
            return await self._read_repo.get_by_customer_id(session, customer_id)
        return res

    async def unlock_memory(
        self,
        customer_id: UUID,
        reason: Optional[str] = "Administrative unlock",
        changed_by: Optional[str] = None,
        session: AsyncSession = None,
    ) -> CustomerMemory:
        """Unlock customer memory."""
        cmd = UnlockMemoryCommand(
            customer_id=customer_id,
            reason=reason,
            actor=changed_by or "API",
        )
        res = await self._command_bus.execute(session, cmd)
        if isinstance(res, dict):
            return await self._read_repo.get_by_customer_id(session, customer_id)
        return res

    async def archive_memory(
        self,
        customer_id: UUID,
        reason: Optional[str] = "Archival transition",
        changed_by: Optional[str] = None,
        session: AsyncSession = None,
    ) -> CustomerMemory:
        """Archive customer memory."""
        cmd = ArchiveMemoryCommand(
            customer_id=customer_id,
            reason=reason,
            actor=changed_by or "API",
        )
        res = await self._command_bus.execute(session, cmd)
        if isinstance(res, dict):
            return await self._read_repo.get_by_customer_id(session, customer_id)
        return res

    async def bulk_create_memories(
        self, requests: List[CustomerMemoryCreateRequest], session: AsyncSession
    ) -> List[CustomerMemory]:
        """Bulk initialize customer memories."""
        results: List[CustomerMemory] = []
        for req in requests:
            mem = await self.create_customer_memory(req, session=session)
            results.append(mem)
        return results

    async def bulk_update_memories(
        self, requests: List[Any], session: AsyncSession
    ) -> List[CustomerMemory]:
        """Bulk update customer memories."""
        results: List[CustomerMemory] = []
        for item in requests:
            cust_id = item.customer_id
            update_data = item.update_data
            mem = await self.update_customer_memory(cust_id, update_data, session=session)
            results.append(mem)
        return results

    # ── Query Methods (Reads) ─────────────────────────────────────────────────

    async def get_customer_memory(
        self,
        customer_id: UUID,
        include_deleted: bool = False,
        session: AsyncSession = None,
    ) -> Optional[CustomerMemory]:
        """Retrieve customer memory record."""
        if not session:
            raise ValueError("AsyncSession is required")
        return await self._read_repo.get_by_customer_id(
            session, customer_id, include_deleted=include_deleted
        )

    async def bulk_get_memories(
        self,
        customer_ids: List[UUID],
        include_deleted: bool = False,
        session: AsyncSession = None,
    ) -> List[CustomerMemory]:
        """Bulk retrieve customer memories."""
        return await self._read_repo.bulk_get(
            session, customer_ids, include_deleted=include_deleted
        )

    async def get_timeline(
        self,
        customer_id: UUID,
        category: Optional[str] = None,
        event_type: Optional[str] = None,
        importance: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
        session: AsyncSession = None,
    ) -> Tuple[List[CustomerMemoryTimelineEvent], int]:
        """Retrieve paginated timeline events."""
        return await self._read_repo.get_timeline(
            session=session,
            customer_id=customer_id,
            category=category,
            event_type=event_type,
            importance=importance,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )

    async def get_versions(
        self,
        customer_id: UUID,
        page: int = 1,
        page_size: int = 50,
        session: AsyncSession = None,
    ) -> Tuple[List[CustomerMemoryVersion], int]:
        """Retrieve paginated version history."""
        return await self._read_repo.get_versions(
            session=session,
            customer_id=customer_id,
            page=page,
            page_size=page_size,
        )

    async def get_version_by_number(
        self, customer_id: UUID, version_number: int, session: AsyncSession = None
    ) -> Optional[CustomerMemoryVersion]:
        """Retrieve specific historical version snapshot."""
        return await self._read_repo.get_version_by_number(
            session=session,
            customer_id=customer_id,
            version_number=version_number,
        )

    async def get_change_logs(
        self,
        customer_id: UUID,
        version_number: Optional[int] = None,
        field_path: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        session: AsyncSession = None,
    ) -> Tuple[List[MemoryChangeLog], int]:
        """Retrieve granular field-level change history."""
        return await self._read_repo.get_change_logs(
            session=session,
            customer_id=customer_id,
            version_number=version_number,
            field_path=field_path,
            page=page,
            page_size=page_size,
        )

    async def get_customer_memory_history(
        self, customer_id: UUID, session: AsyncSession = None
    ) -> CustomerMemoryHistoryResponse:
        """
        Unified history query returning current memory state, timeline,
        versions, and change logs in a single payload.
        """
        memory = await self._read_repo.get_by_customer_id(session, customer_id, include_deleted=True)
        timeline_events, _ = await self._read_repo.get_timeline(session, customer_id=customer_id, page=1, page_size=50)
        versions, _ = await self._read_repo.get_versions(session, customer_id=customer_id, page=1, page_size=50)
        change_logs, _ = await self._read_repo.get_change_logs(session, customer_id=customer_id, page=1, page_size=100)

        mem_resp = CustomerMemoryResponse.model_validate(memory) if memory else None
        timeline_resps = [CustomerMemoryTimelineEventResponse.model_validate(e) for e in timeline_events]
        version_resps = [CustomerMemoryVersionResponse.model_validate(v) for v in versions]
        log_resps = [MemoryChangeLogResponse.model_validate(l) for l in change_logs]

        return CustomerMemoryHistoryResponse(
            memory=mem_resp,
            timeline=timeline_resps,
            versions=version_resps,
            change_logs=log_resps,
        )

    async def search_memory(
        self, request: MemorySearchRequest, session: AsyncSession = None
    ) -> CustomerMemorySearchResponse:
        """Execute multi-criteria search over memory records."""
        items, total = await self._read_repo.search(
            session=session,
            workspace_id=request.workspace_id,
            search_term=request.search_term,
            current_stage=request.current_stage,
            tags=request.tags,
            location_city=request.location_city,
            min_budget=request.min_budget,
            max_budget=request.max_budget,
            property_types=request.property_types,
            lifecycle_status=request.lifecycle_status,
            page=request.page,
            page_size=request.page_size,
        )

        result_items = [
            CustomerMemorySearchResultItem(
                id=m.id,
                customer_id=m.customer_id,
                workspace_id=m.workspace_id,
                version_number=m.version_number,
                revision_id=m.revision_id,
                lifecycle_status=m.lifecycle_status,
                memory_payload=m.memory_payload,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in items
        ]

        return CustomerMemorySearchResponse(
            items=result_items,
            total=total,
            page=request.page,
            page_size=request.page_size,
        )
