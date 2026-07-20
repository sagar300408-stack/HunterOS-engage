"""
Dashboard API — All dashboard endpoints + WebSocket.

Endpoints:
    GET  /api/v1/dashboard/overview
    GET  /api/v1/dashboard/conversations
    GET  /api/v1/dashboard/conversations/{id}
    GET  /api/v1/dashboard/customers
    GET  /api/v1/dashboard/customers/{id}
    PUT  /api/v1/dashboard/customers/{id}
    GET  /api/v1/dashboard/analytics
    GET  /api/v1/dashboard/system-health
    GET  /api/v1/dashboard/activity
    GET  /api/v1/dashboard/leads
    PUT  /api/v1/dashboard/leads/{customer_id}/stage
    GET  /api/v1/dashboard/queue
    GET  /api/v1/dashboard/audit-log
    GET  /api/v1/dashboard/search
    WS   /ws/dashboard

RBAC:
    - All GET endpoints: view_all (Sales, Support, Reader, Admin, Founder)
    - PUT /customers/{id}: edit_memory (Sales, Support, Admin, Founder)
    - PUT /leads/{id}/stage: change_lead_stage (Sales, Admin, Founder)
"""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth_deps import get_current_user, require_permission
from app.domain.dashboard import service as dash_service
from app.domain.security.models import DEFAULT_WORKSPACE_ID, User
from app.domain.dashboard.schemas import (
    ActivityEvent,
    AnalyticsData,
    AuditLogSchema,
    ConversationDetail,
    ConversationPage,
    CustomerPage,
    CustomerProfile,
    LeadPipeline,
    OverviewMetrics,
    QueueStatus,
    SearchResults,
    SystemHealth,
    UpdateCustomerRequest,
    UpdateLeadStageRequest,
)
from app.integrations.postgres.database import get_db
from app.integrations.websocket.manager import ws_manager
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard v1"])
ws_router = APIRouter(tags=["Dashboard WebSocket"])
logger = get_logger(__name__)

# Convenience alias — reduces boilerplate in each route
_view = Depends(require_permission("view_all"))


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get(
    "/overview",
    response_model=OverviewMetrics,
    summary="Dashboard KPI Overview",
    description="Returns all 9 metric cards for the dashboard header.",
)
async def get_overview(
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> OverviewMetrics:
    return await dash_service.get_overview_metrics(session, user.workspace_id)


# ── Conversations ─────────────────────────────────────────────────────────────

@router.get(
    "/conversations",
    response_model=ConversationPage,
    summary="Live Conversation Feed",
)
async def get_conversations(
    search: Optional[str] = Query(None, description="Search by customer name or phone"),
    buying_stage: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> ConversationPage:
    
    return await dash_service.get_conversations(
        session=session,
        workspace_id=user.workspace_id,
        search=search,
        buying_stage=buying_stage,
        page=page,
        page_size=page_size,        )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Conversation Detail + Pipeline Events",
)
async def get_conversation_detail(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> ConversationDetail:
    result = await dash_service.get_conversation_detail(session, conversation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get(
    "/customers",
    response_model=CustomerPage,
    summary="Customer List",
)
async def get_customers(
    search: Optional[str] = Query(None),
    buying_stage: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> CustomerPage:
    return await dash_service.get_customers(
        session=session,
        workspace_id=user.workspace_id,
        search=search,
        buying_stage=buying_stage,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerProfile,
    summary="Customer Profile — Full View",
)
async def get_customer_profile(
    customer_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> CustomerProfile:
    result = await dash_service.get_customer_profile(session, customer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result


@router.put(
    "/customers/{customer_id}",
    status_code=204,
    summary="Update Customer Details",
    description="Requires edit_memory permission (Sales, Support, Admin, Founder).",
)
async def update_customer(
    customer_id: UUID,
    body: UpdateCustomerRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("edit_memory")),
) -> None:
    await dash_service.update_customer(
        session=session,
        customer_id=customer_id,
        updates=body.model_dump(exclude_none=True),
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
        workspace_id=user.workspace_id,
    )
    # Broadcast update to live dashboard clients
    await ws_manager.broadcast({
        "event": "customer_updated",
        "data": {"customer_id": str(customer_id)},
    })


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get(
    "/analytics",
    response_model=AnalyticsData,
    summary="Analytics Charts + AI Cost Metrics",
)
async def get_analytics(
    date_from: Optional[date] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[date] = Query(None, description="End date YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> AnalyticsData:
    return await dash_service.get_analytics(
            session=session,
            workspace_id=user.workspace_id,
            date_from=date_from,
            date_to=date_to,
    )


# ── System Health ─────────────────────────────────────────────────────────────

@router.get(
    "/system-health",
    response_model=SystemHealth,
    summary="System Health Check",
)
async def get_system_health(
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> SystemHealth:
    
    return await dash_service.get_system_health(session)


# ── Activity Feed ─────────────────────────────────────────────────────────────

@router.get(
    "/activity",
    response_model=list[ActivityEvent],
    summary="AI Activity Timeline",
)
async def get_activity(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> list[ActivityEvent]:
    return await dash_service.get_activity_feed(session, user.workspace_id, limit)


# ── Lead Pipeline ─────────────────────────────────────────────────────────────

@router.get(
    "/leads",
    response_model=LeadPipeline,
    summary="Kanban Lead Pipeline",
)
async def get_leads(
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> LeadPipeline:
    return await dash_service.get_lead_pipeline(session, user.workspace_id)


@router.put(
    "/leads/{customer_id}/stage",
    status_code=204,
    summary="Move Lead to Stage",
    description="Requires change_lead_stage permission (Sales, Admin, Founder).",
)
async def update_lead_stage(
    customer_id: UUID,
    body: UpdateLeadStageRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("change_lead_stage")),
) -> None:
    
    await dash_service.update_lead_stage(
        session=session,
        customer_id=customer_id,
        new_stage=body.buying_stage,
        actor_user_id=user.id,
        reason=body.reason,
        ip_address=request.client.host if request.client else None,
        workspace_id=user.workspace_id,
    )
    await ws_manager.broadcast({
        "event": "lead_stage_changed",
        "data": {
            "customer_id": str(customer_id),
            "new_stage": body.buying_stage,
        },
    })


# ── Queue Monitor ─────────────────────────────────────────────────────────────

@router.get(
    "/queue",
    response_model=QueueStatus,
    summary="Queue Monitor",
    description="Displays pending, running, and failed background jobs.",
)
async def get_queue(
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> QueueStatus:
    return await dash_service.get_queue_status(session, user.workspace_id)


# ── Audit Log ─────────────────────────────────────────────────────────────────

@router.get(
    "/audit-log",
    response_model=list[AuditLogSchema],
    summary="Audit Log",
    description="Immutable history of all manual dashboard mutations.",
)
async def get_audit_log(
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("view_all")),
) -> list[AuditLogSchema]:
    
    return await dash_service.get_audit_log(session, user.workspace_id, limit)


# ── Search ────────────────────────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=SearchResults,
    summary="Search Everything",
    description="Unified search across customers, conversations, memory, and intents.",
)
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(30, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    user: User = _view,
) -> SearchResults:
    return await dash_service.search_everything(
        session=session,
        query=q,
        workspace_id=user.workspace_id,
        limit=limit,
    )


# ── WebSocket ─────────────────────────────────────────────────────────────────

@ws_router.websocket("/ws/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    WebSocket endpoint for real-time dashboard updates.

    Authentication: pass JWT as ?token=<jwt> query parameter.

    Events pushed from server:
        conversation_updated  — new message arrived
        intent_extracted      — intent classification complete
        memory_updated        — customer memory refreshed
        lead_stage_changed    — buying stage updated
        customer_updated      — customer profile changed
        system_notification   — high-value lead, error, etc.
    """
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user = await get_user_from_token(session, token)
    if not user:
        await websocket.close(code=4003, reason="Invalid token")
        return

    await ws_manager.connect(websocket)
    logger.info("ws_dashboard_connected", user_email=user.email)

    # Send initial connection confirmation
    await ws_manager.send_to(websocket, {
        "event": "connected",
        "data": {
            "user": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "clients": ws_manager.connection_count,
        },
    })

    try:
        while True:
            # Keep connection alive — client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await ws_manager.send_to(websocket, {"event": "pong", "data": {}})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("ws_dashboard_disconnected", user_email=user.email)


# Re-export get_user_from_token for ws route
from app.domain.dashboard.service import get_user_from_token  # noqa: E402
