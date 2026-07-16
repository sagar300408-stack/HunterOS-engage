from datetime import date
from typing import Any, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.ext.asyncio import AsyncSession

# from app.database import get_db_session  (Assuming a session dependency exists somewhere)
from app.api.v1.auth_deps import get_current_user
from app.domain.analytics.repository import AnalyticsRepository
from app.domain.analytics.schemas import AnalyticsMetricResponse
from app.domain.analytics.service import AnalyticsQueryService
from app.domain.dashboard.models import User
from app.domain.livestream.manager import livestream_manager
from app.domain.timeline.repository import TimelineRepository
from app.domain.timeline.schemas import TimelineEntryResponse
from app.domain.timeline.service import TimelineQueryService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/livestream", tags=["Live Stream"])
ws_router = APIRouter(tags=["Live Stream WebSocket"])

def get_analytics_service() -> AnalyticsQueryService:
    repo = AnalyticsRepository()
    return AnalyticsQueryService(repo)

def get_timeline_service() -> TimelineQueryService:
    repo = TimelineRepository()
    return TimelineQueryService(repo)


# ── REST Dashboard Projection API ─────────────────────────────────────────────

@router.get("/workspace/{workspace_id}/activity", response_model=List[TimelineEntryResponse])
async def get_recent_activity(
    workspace_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    # session: AsyncSession = Depends(get_db_session),
    # user: User = Depends(get_current_user),
    timeline_service: TimelineQueryService = Depends(get_timeline_service)
):
    """
    Consumes the Timeline projection to return recent activity for a workspace.
    This does NOT query business subsystems directly.
    """
    # Assuming the caller resolves session. For this skeleton we pass None
    session = None
    return await timeline_service.get_workspace_timeline(session, workspace_id, limit=limit)


@router.get("/workspace/{workspace_id}/analytics", response_model=List[AnalyticsMetricResponse])
async def get_analytics_summary(
    workspace_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    # session: AsyncSession = Depends(get_db_session),
    # user: User = Depends(get_current_user),
    analytics_service: AnalyticsQueryService = Depends(get_analytics_service)
):
    """
    Consumes the Analytics projection to return summary metrics.
    This does NOT query business subsystems directly.
    """
    session = None
    return await analytics_service.get_workspace_metrics(session, workspace_id, start_date, end_date)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@ws_router.websocket("/ws/workspace/{workspace_id}")
async def websocket_livestream(
    websocket: WebSocket,
    workspace_id: UUID,
    token: Optional[str] = Query(None),
    # session: AsyncSession = Depends(get_db_session),
) -> None:
    """
    WebSocket endpoint for strict Workspace-isolated Live Operational Intelligence.
    Only delivers events that belong to the requested workspace.
    Reconnection should rely on querying the REST Projection APIs for history.
    """
    # Optional Auth logic could go here:
    # if not token or not valid:
    #     await websocket.close(code=4001, reason="Missing or invalid token")
    #     return

    await livestream_manager.connect(workspace_id, websocket)
    
    # Send initial connection confirmation
    await livestream_manager.send_to(websocket, {
        "event": "connected",
        "data": {
            "workspace_id": str(workspace_id),
            "status": "listening",
        }
    })

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await livestream_manager.send_to(websocket, {"event": "pong"})
    except WebSocketDisconnect:
        await livestream_manager.disconnect(workspace_id, websocket)
