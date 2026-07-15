from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Assuming a get_db_session dependency exists in the main app
# from app.database import get_db_session

from app.domain.timeline.repository import TimelineRepository
from app.domain.timeline.schemas import TimelineEntryResponse
from app.domain.timeline.service import TimelineQueryService

router = APIRouter(prefix="/timeline", tags=["Timeline"])

def get_timeline_query_service() -> TimelineQueryService:
    repository = TimelineRepository()
    return TimelineQueryService(repository)

@router.get("/workspace/{workspace_id}", response_model=List[TimelineEntryResponse])
async def get_workspace_timeline(
    workspace_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # session: AsyncSession = Depends(get_db_session),
    service: TimelineQueryService = Depends(get_timeline_query_service)
):
    """
    Retrieve the activity timeline for an entire workspace.
    """
    # Placeholder for DB session
    session = None
    return await service.get_workspace_timeline(session, workspace_id, limit, offset)

@router.get("/customer/{workspace_id}/{customer_id}", response_model=List[TimelineEntryResponse])
async def get_customer_timeline(
    workspace_id: UUID,
    customer_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # session: AsyncSession = Depends(get_db_session),
    service: TimelineQueryService = Depends(get_timeline_query_service)
):
    """
    Retrieve the activity timeline specific to a customer.
    """
    session = None
    return await service.get_customer_timeline(session, workspace_id, customer_id, limit, offset)

@router.get("/conversation/{workspace_id}/{conversation_id}", response_model=List[TimelineEntryResponse])
async def get_conversation_timeline(
    workspace_id: UUID,
    conversation_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # session: AsyncSession = Depends(get_db_session),
    service: TimelineQueryService = Depends(get_timeline_query_service)
):
    """
    Retrieve the activity timeline specific to a conversation.
    """
    session = None
    return await service.get_conversation_timeline(session, workspace_id, conversation_id, limit, offset)
