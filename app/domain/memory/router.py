"""
HunterOS Engage — Customer Memory REST API Router

Exposes foundational memory infrastructure endpoints for creating, retrieving,
updating (PATCH), replacing (PUT), status transition, soft-deleting, versioning,
timeline logging, unified history queries, and multi-criteria search.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.memory.models import (
    InvalidLifecycleTransitionError,
    LifecycleStatus,
    MemoryConcurrencyConflictError,
    MemoryDomainError,
    MemoryImportance,
    MemoryLockedError,
    MemoryTimelineCategory,
)
from app.domain.memory.queries.models import (
    CustomerMemoryDTO,
    MemoryExportDTO,
    MemoryStatisticsDTO,
    ProjectedMemoryDTO,
)
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
    CustomerMemoryStatusChangeRequest,
    CustomerMemoryTimelineEventResponse,
    CustomerMemoryUpdateRequest,
    CustomerMemoryVersionDetailResponse,
    CustomerMemoryVersionResponse,
    MemoryChangeLogListResponse,
    MemoryChangeLogResponse,
    MemoryCursorSearchRequest,
    MemoryCursorSearchResponse,
    MemoryExportPreviewRequest,
    MemoryProjectionRequest,
    MemorySearchRequest,
    MemoryTimelineListResponse,
)
from app.domain.memory.service import MemoryService
from app.domain.memory.validators.base import MemoryValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/memory", tags=["Customer Memory Operations & Lifecycle"])


def get_memory_service() -> MemoryService:
    """Dependency provider for MemoryService."""
    return MemoryService()


def _set_etag(response: Response, revision_id: str) -> None:
    """Sets ETag header for caching and optimistic concurrency control."""
    response.headers["ETag"] = f'"{revision_id}"'


def _clean_etag(etag: Optional[str]) -> Optional[str]:
    """Strips quotes and whitespace from ETag / If-Match header value."""
    if not etag:
        return None
    return etag.strip(' "')


# ── Core Memory Endpoints ─────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CustomerMemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Customer Memory",
    description="Initialize structured memory for a customer and generate baseline version 1 snapshot.",
)
async def create_memory(
    request: CustomerMemoryCreateRequest,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    if idempotency_key:
        request.idempotency_key = idempotency_key

    try:
        memory = await service.create_customer_memory(request, session=db)
        _set_etag(response, memory.revision_id)
        resp = CustomerMemoryResponse.model_validate(memory)
        resp.etag = f'"{memory.revision_id}"'
        return resp
    except MemoryValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except (ValueError, MemoryDomainError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error("memory_create_failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create customer memory: {str(e)}",
        )


@router.get(
    "/{customer_id}",
    response_model=CustomerMemoryResponse,
    summary="Get Customer Memory",
    description="Retrieve the active structured memory for a customer.",
)
async def get_memory(
    customer_id: UUID,
    response: Response,
    include_deleted: bool = Query(False, description="Whether to include soft-deleted memory"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    memory = await service.get_customer_memory(customer_id, include_deleted=include_deleted, session=db)
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer memory not found for customer {customer_id}",
        )
    _set_etag(response, memory.revision_id)
    resp = CustomerMemoryResponse.model_validate(memory)
    resp.etag = f'"{memory.revision_id}"'
    return resp


@router.patch(
    "/{customer_id}",
    response_model=CustomerMemoryResponse,
    summary="Update Customer Memory (PATCH)",
    description="Partially update memory fields. Enforces OCC with revision_id / If-Match header.",
)
async def update_memory(
    customer_id: UUID,
    request: CustomerMemoryUpdateRequest,
    response: Response,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    if if_match and not request.expected_revision_id:
        request.expected_revision_id = _clean_etag(if_match)
    if idempotency_key and not request.idempotency_key:
        request.idempotency_key = idempotency_key

    try:
        memory = await service.update_customer_memory(customer_id, request, session=db)
        _set_etag(response, memory.revision_id)
        resp = CustomerMemoryResponse.model_validate(memory)
        resp.etag = f'"{memory.revision_id}"'
        return resp
    except MemoryConcurrencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(e))
    except MemoryLockedError as e:
        raise HTTPException(status_code=423, detail=str(e))
    except MemoryValidationError as e:
        if any("LOCKED" in str(err) for err in e.errors):
            raise HTTPException(status_code=423, detail=str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("memory_update_failed", extra={"error": str(e), "customer_id": str(customer_id)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update customer memory: {str(e)}",
        )


@router.put(
    "/{customer_id}",
    response_model=CustomerMemoryResponse,
    summary="Replace Customer Memory (PUT)",
    description="Completely replace memory payload. Enforces OCC with revision_id / If-Match header.",
)
async def replace_memory(
    customer_id: UUID,
    request: CustomerMemoryReplaceRequest,
    response: Response,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    if if_match and not request.expected_revision_id:
        request.expected_revision_id = _clean_etag(if_match)
    if idempotency_key and not request.idempotency_key:
        request.idempotency_key = idempotency_key

    try:
        memory = await service.replace_customer_memory(customer_id, request, session=db)
        _set_etag(response, memory.revision_id)
        resp = CustomerMemoryResponse.model_validate(memory)
        resp.etag = f'"{memory.revision_id}"'
        return resp
    except MemoryConcurrencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(e))
    except MemoryLockedError as e:
        raise HTTPException(status_code=423, detail=str(e))
    except MemoryValidationError as e:
        if any("LOCKED" in str(err) for err in e.errors):
            raise HTTPException(status_code=423, detail=str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("memory_replace_failed", extra={"error": str(e), "customer_id": str(customer_id)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replace customer memory: {str(e)}",
        )


@router.delete(
    "/{customer_id}",
    response_model=CustomerMemoryResponse,
    summary="Soft Delete Customer Memory",
    description="Soft delete customer memory record and create deletion audit trail in timeline & versions.",
)
async def soft_delete_memory(
    customer_id: UUID,
    reason: Optional[str] = Query(None, description="Reason for deletion"),
    changed_by: Optional[str] = Query("API", description="Actor performing deletion"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    try:
        memory = await service.soft_delete_memory(customer_id, reason=reason, changed_by=changed_by, session=db)
        return CustomerMemoryResponse.model_validate(memory)
    except MemoryLockedError as e:
        raise HTTPException(status_code=423, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{customer_id}/restore",
    response_model=CustomerMemoryResponse,
    summary="Restore Customer Memory",
    description="Restore a previously soft-deleted customer memory record.",
)
async def restore_memory(
    customer_id: UUID,
    changed_by: Optional[str] = Query("API", description="Actor performing restoration"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    try:
        memory = await service.restore_memory(customer_id, changed_by=changed_by, session=db)
        return CustomerMemoryResponse.model_validate(memory)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{customer_id}/status",
    response_model=CustomerMemoryResponse,
    summary="Change Lifecycle Status",
    description="Transitions memory lifecycle status (ACTIVE, LOCKED, ARCHIVED, etc.).",
)
async def change_status(
    customer_id: UUID,
    request: CustomerMemoryStatusChangeRequest,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    try:
        memory = await service.change_lifecycle_status(
            customer_id=customer_id,
            target_status=request.target_status,
            reason=request.reason,
            changed_by=request.changed_by,
            session=db,
        )
        return CustomerMemoryResponse.model_validate(memory)
    except InvalidLifecycleTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MemoryDomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{customer_id}/lock",
    response_model=CustomerMemoryResponse,
    summary="Lock Customer Memory",
    description="Administratively locks customer memory against further mutations.",
)
async def lock_memory(
    customer_id: UUID,
    reason: Optional[str] = Query("Administrative lock", description="Reason for lock"),
    changed_by: Optional[str] = Query("API", description="Actor performing lock"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    try:
        memory = await service.lock_memory(customer_id, reason=reason, changed_by=changed_by, session=db)
        return CustomerMemoryResponse.model_validate(memory)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{customer_id}/unlock",
    response_model=CustomerMemoryResponse,
    summary="Unlock Customer Memory",
    description="Unlocks previously locked customer memory.",
)
async def unlock_memory(
    customer_id: UUID,
    reason: Optional[str] = Query("Administrative unlock", description="Reason for unlock"),
    changed_by: Optional[str] = Query("API", description="Actor performing unlock"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    try:
        memory = await service.unlock_memory(customer_id, reason=reason, changed_by=changed_by, session=db)
        return CustomerMemoryResponse.model_validate(memory)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{customer_id}/archive",
    response_model=CustomerMemoryResponse,
    summary="Archive Customer Memory",
    description="Places customer memory into read-only ARCHIVED state.",
)
async def archive_memory(
    customer_id: UUID,
    reason: Optional[str] = Query("Archival transition", description="Reason for archiving"),
    changed_by: Optional[str] = Query("API", description="Actor performing archival"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryResponse:
    try:
        memory = await service.archive_memory(customer_id, reason=reason, changed_by=changed_by, session=db)
        return CustomerMemoryResponse.model_validate(memory)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Timeline & Versioning Endpoints ───────────────────────────────────────────

@router.get(
    "/{customer_id}/timeline",
    response_model=MemoryTimelineListResponse,
    summary="Get Memory Timeline",
    description="Retrieve chronologically ordered timeline events for a customer with category and importance filtering.",
)
async def get_timeline(
    customer_id: UUID,
    category: Optional[MemoryTimelineCategory] = Query(None, description="Timeline category"),
    event_type: Optional[str] = Query(None, description="Event type identifier"),
    importance: Optional[MemoryImportance] = Query(None, description="Importance level"),
    start_time: Optional[datetime] = Query(None, description="Filter events after start_time"),
    end_time: Optional[datetime] = Query(None, description="Filter events before end_time"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryTimelineListResponse:
    items, total = await service.get_timeline(
        customer_id=customer_id,
        category=category.value if category else None,
        event_type=event_type,
        importance=importance.value if importance else None,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
        session=db,
    )
    res_items = [CustomerMemoryTimelineEventResponse.model_validate(e) for e in items]
    return MemoryTimelineListResponse(items=res_items, total=total, page=page, page_size=page_size)


@router.get(
    "/{customer_id}/versions",
    response_model=List[CustomerMemoryVersionResponse],
    summary="Get Memory Versions",
    description="Retrieve version history list for a customer.",
)
async def get_versions(
    customer_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> List[CustomerMemoryVersionResponse]:
    versions, _ = await service.get_versions(customer_id, page=page, page_size=page_size, session=db)
    return [CustomerMemoryVersionResponse.model_validate(v) for v in versions]


@router.get(
    "/{customer_id}/versions/{version_number}",
    response_model=CustomerMemoryVersionDetailResponse,
    summary="Get Specific Version Snapshot",
    description="Retrieve full frozen memory snapshot data for a specific historical version.",
)
async def get_version_detail(
    customer_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryVersionDetailResponse:
    version = await service.get_version_by_number(customer_id, version_number, session=db)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for customer {customer_id}",
        )
    return CustomerMemoryVersionDetailResponse.model_validate(version)


@router.get(
    "/{customer_id}/changelog",
    response_model=MemoryChangeLogListResponse,
    summary="Get Memory Change Log",
    description="Retrieve field-level granular changes with module attribution.",
)
async def get_changelog(
    customer_id: UUID,
    version_number: Optional[int] = Query(None, description="Filter by version number"),
    field_path: Optional[str] = Query(None, description="Filter by field path pattern"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryChangeLogListResponse:
    logs, total = await service.get_change_logs(
        customer_id=customer_id,
        version_number=version_number,
        field_path=field_path,
        page=page,
        page_size=page_size,
        session=db,
    )
    res_items = [MemoryChangeLogResponse.model_validate(l) for l in logs]
    return MemoryChangeLogListResponse(items=res_items, total=total, page=page, page_size=page_size)


@router.get(
    "/{customer_id}/history",
    response_model=CustomerMemoryHistoryResponse,
    summary="Get Unified Customer Memory History",
    description="Aggregates current memory state, chronological timeline events, historical versions, and change logs in a single request.",
)
async def get_customer_memory_history(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemoryHistoryResponse:
    return await service.get_customer_memory_history(customer_id, session=db)


# ── Search & Bulk Endpoints ───────────────────────────────────────────────────

@router.post(
    "/search",
    response_model=CustomerMemorySearchResponse,
    summary="Search Customer Memories",
    description="Multi-criteria search across customer memory records (locations, budgets, stages, tags, terms).",
)
async def search_memories(
    request: MemorySearchRequest,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> CustomerMemorySearchResponse:
    return await service.search_memory(request, session=db)


@router.post(
    "/bulk",
    response_model=List[CustomerMemoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk Create Customer Memories",
    description="Initialize multiple customer memory records in a single batch operation.",
)
async def bulk_create_memories(
    request: CustomerMemoryBulkCreateRequest,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> List[CustomerMemoryResponse]:
    try:
        memories = await service.bulk_create_memories(request.items, session=db)
        return [CustomerMemoryResponse.model_validate(m) for m in memories]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/bulk-get",
    response_model=List[CustomerMemoryResponse],
    summary="Bulk Retrieve Customer Memories",
    description="Fetch multiple customer memory records by customer IDs.",
)
async def bulk_get_memories(
    request: CustomerMemoryBulkGetRequest,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> List[CustomerMemoryResponse]:
    memories = await service.bulk_get_memories(
        request.customer_ids, include_deleted=request.include_deleted, session=db
    )
    return [CustomerMemoryResponse.model_validate(m) for m in memories]


@router.post(
    "/bulk-update",
    response_model=List[CustomerMemoryResponse],
    summary="Bulk Update Customer Memories",
    description="Update multiple customer memories in batch.",
)
async def bulk_update_memories(
    request: CustomerMemoryBulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> List[CustomerMemoryResponse]:
    try:
        memories = await service.bulk_update_memories(request.items, session=db)
        return [CustomerMemoryResponse.model_validate(m) for m in memories]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Memory Query Intelligence Endpoints (Phase 2.1.3) ─────────────────────────

@router.post(
    "/search/cursor",
    response_model=MemoryCursorSearchResponse,
    summary="Cursor-Paginated Memory Search",
    description="High-performance keyset cursor pagination across customer memories with workspace token validation.",
)
async def search_memories_cursor(
    request: MemoryCursorSearchRequest,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryCursorSearchResponse:
    result = await service.query_facade.search_memories_cursor(
        workspace_id=request.workspace_id,
        cursor=request.cursor,
        limit=request.limit,
        session=db,
    )
    items = [
        CustomerMemorySearchResultItem(
            id=dto.id,
            customer_id=dto.customer_id,
            workspace_id=dto.workspace_id,
            version_number=dto.version_number,
            revision_id=dto.revision_id,
            lifecycle_status=LifecycleStatus(dto.lifecycle_status),
            memory_payload=dto.memory_payload,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
        for dto in result.items
    ]
    return MemoryCursorSearchResponse(
        items=items,
        next_cursor=result.next_cursor,
        prev_cursor=result.prev_cursor,
        has_more=result.has_more,
        limit=result.limit,
    )


@router.post(
    "/{customer_id}/projection",
    summary="Get Memory Projection View",
    description="Retrieve named versioned projection view (SUMMARY, EXECUTIVE, LIGHTWEIGHT) or custom field mask.",
)
async def get_memory_projection(
    customer_id: UUID,
    request: MemoryProjectionRequest,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> Any:
    projected = await service.query_facade.get_projection(
        customer_id=customer_id,
        view_name=request.view_name,
        projection_mask=request.projection_mask,
        projection_version=request.projection_version,
        bypass_cache=request.bypass_cache,
        session=db,
    )
    if not projected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer memory for '{customer_id}' not found.",
        )
    return projected


@router.get(
    "/analytics/statistics",
    response_model=MemoryStatisticsDTO,
    summary="Get Memory Subsystem Statistics",
    description="Aggregated lifecycle distributions, storage sizing, version metrics, and operational query performance telemetry.",
)
async def get_memory_statistics(
    workspace_id: Optional[UUID] = Query(None, description="Optional workspace scope"),
    bypass_cache: bool = Query(False, description="Bypass cache for real-time calculation"),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryStatisticsDTO:
    return await service.query_facade.get_statistics(
        workspace_id=workspace_id,
        bypass_cache=bypass_cache,
        session=db,
    )


@router.post(
    "/export/preview",
    response_model=MemoryExportDTO,
    summary="Preview Tabular Memory Export",
    description="Generate tabular preview dataset suitable for CSV/Excel transformations.",
)
async def preview_memory_export(
    request: MemoryExportPreviewRequest,
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryExportDTO:
    return await service.query_facade.preview_export(
        workspace_id=request.workspace_id,
        export_format=request.export_format,
        columns=request.columns,
        max_rows=request.max_rows,
        session=db,
    )

