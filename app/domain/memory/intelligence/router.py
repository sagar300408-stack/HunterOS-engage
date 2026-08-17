"""
HunterOS Engage — Memory Context REST Router (Phase 2.1.5)

Exposes the frozen public Memory Context API v1 endpoints for downstream intelligence modules.
"""

from __future__ import annotations

import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.memory.intelligence.gateway import (
    MemoryContextGateway,
    get_memory_context_gateway,
)
from app.domain.memory.intelligence.models import (
    ContextScope,
    ExportTargetFormat,
)
from app.domain.memory.intelligence.schemas import (
    ContextRequestOptions,
    CustomContextRequest,
    CustomerContextResponse,
    DashboardContextExportDTO,
    ExecutiveContextExportDTO,
    ExecutiveContextResponse,
    OpportunityContextResponse,
    OrganizationContextResponse,
    PropertyContextResponse,
    StructuredContextDTO,
)

router = APIRouter(prefix="/context", tags=["Memory Context & Intelligence Gateway"])


@router.get("/customer/{customer_id}")
async def get_customer_context(
    customer_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID] = Query(None),
    max_depth: int = Query(2, ge=1, le=5),
    include_timeline: bool = Query(True),
    include_versions: bool = Query(False),
    include_statistics: bool = Query(True),
    include_projections: bool = Query(True),
    format: Optional[ExportTargetFormat] = Query(None),
    gateway: MemoryContextGateway = Depends(get_memory_context_gateway),
) -> Any:
    """Retrieve assembled Customer 360 Context."""
    options = ContextRequestOptions(
        max_graph_depth=max_depth,
        include_timeline=include_timeline,
        include_versions=include_versions,
        include_statistics=include_statistics,
        include_projections=include_projections,
        format=format,
    )
    res = await gateway.get_customer_context(
        customer_id=customer_id,
        workspace_id=workspace_id,
        options=options,
    )
    return res


@router.get("/organization/{org_id}")
async def get_organization_context(
    org_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID] = Query(None),
    max_depth: int = Query(2, ge=1, le=5),
    format: Optional[ExportTargetFormat] = Query(None),
    gateway: MemoryContextGateway = Depends(get_memory_context_gateway),
) -> Any:
    """Retrieve assembled Organization & Company Context."""
    options = ContextRequestOptions(
        max_graph_depth=max_depth,
        format=format,
    )
    res = await gateway.get_organization_context(
        org_id=org_id,
        workspace_id=workspace_id,
        options=options,
    )
    return res


@router.get("/opportunity/{opp_id}")
async def get_opportunity_context(
    opp_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID] = Query(None),
    max_depth: int = Query(2, ge=1, le=5),
    format: Optional[ExportTargetFormat] = Query(None),
    gateway: MemoryContextGateway = Depends(get_memory_context_gateway),
) -> Any:
    """Retrieve assembled Opportunity Context."""
    options = ContextRequestOptions(
        max_graph_depth=max_depth,
        format=format,
    )
    res = await gateway.get_opportunity_context(
        opportunity_id=opp_id,
        workspace_id=workspace_id,
        options=options,
    )
    return res


@router.get("/property/{prop_id}")
async def get_property_context(
    prop_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID] = Query(None),
    max_depth: int = Query(2, ge=1, le=5),
    format: Optional[ExportTargetFormat] = Query(None),
    gateway: MemoryContextGateway = Depends(get_memory_context_gateway),
) -> Any:
    """Retrieve assembled Property Context."""
    options = ContextRequestOptions(
        max_graph_depth=max_depth,
        format=format,
    )
    res = await gateway.get_property_context(
        property_id=prop_id,
        workspace_id=workspace_id,
        options=options,
    )
    return res


@router.get("/executive")
async def get_executive_context(
    workspace_id: Optional[uuid.UUID] = Query(None),
    format: Optional[ExportTargetFormat] = Query(None),
    gateway: MemoryContextGateway = Depends(get_memory_context_gateway),
) -> Any:
    """Retrieve Workspace Executive Context."""
    options = ContextRequestOptions(format=format)
    res = await gateway.get_executive_context(
        workspace_id=workspace_id,
        options=options,
    )
    return res


@router.post("/custom")
async def get_custom_context(
    req: CustomContextRequest,
    gateway: MemoryContextGateway = Depends(get_memory_context_gateway),
) -> Any:
    """Retrieve custom arbitrary entity context."""
    options = ContextRequestOptions(
        blocks=req.blocks,
        max_graph_depth=req.max_graph_depth,
        format=req.format,
    )
    res = await gateway.get_custom_context(
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        workspace_id=req.workspace_id,
        options=options,
    )
    return res


@router.post("/export")
async def export_context(
    scope: ContextScope,
    entity_id: Optional[str] = Query(None),
    workspace_id: Optional[uuid.UUID] = Query(None),
    target_format: ExportTargetFormat = Query(ExportTargetFormat.STRUCTURED_CONTEXT),
    gateway: MemoryContextGateway = Depends(get_memory_context_gateway),
) -> Any:
    """Export composed context in specialized target format."""
    res = await gateway.export_context(
        scope=scope,
        entity_id=entity_id,
        workspace_id=workspace_id,
        target_format=target_format,
    )
    return res
