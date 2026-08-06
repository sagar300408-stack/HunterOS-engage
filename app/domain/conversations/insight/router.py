"""
HunterOS Engage V1 - Conversation Insight REST API Router
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine

FastAPI endpoints for querying business insights, risks, opportunities,
action items, and rendering multi-perspective views.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.conversations.insight.engine import (
    ConversationInsightEngine,
    default_conversation_insight_engine,
)
from app.domain.conversations.insight.models import (
    InsightCategory,
    InsightPriority,
)
from app.domain.conversations.insight.repository import (
    InMemoryInsightRepository,
    default_insight_repository,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversation Intelligence - Insights"],
)


@router.get(
    "/insights/{insight_result_id}",
    summary="Get Conversation Insight Result by ID",
    response_model=Dict[str, Any],
)
async def get_insight_by_id(
    insight_result_id: uuid.UUID,
    repo: InMemoryInsightRepository = Depends(lambda: default_insight_repository),
) -> Dict[str, Any]:
    """Retrieves an insight aggregate root by its UUID."""
    result = repo.get_by_id(insight_result_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation insight result '{insight_result_id}' not found.",
        )
    return result.model_dump()


@router.get(
    "/{conversation_id}/insights",
    summary="Get Latest Insights for Conversation",
    response_model=Dict[str, Any],
)
async def get_conversation_insights(
    conversation_id: str,
    repo: InMemoryInsightRepository = Depends(lambda: default_insight_repository),
) -> Dict[str, Any]:
    """Retrieves the latest insight result for a specific conversation."""
    result = repo.get_latest_by_conversation(conversation_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No insight results found for conversation '{conversation_id}'.",
        )
    return result.model_dump()


@router.get(
    "/{conversation_id}/insights/risks",
    summary="Get Conversation Risks with Optional Filters",
    response_model=List[Dict[str, Any]],
)
async def get_conversation_risks(
    conversation_id: str,
    priority: Optional[InsightPriority] = Query(None, description="Filter by risk priority"),
    category: Optional[InsightCategory] = Query(None, description="Filter by risk category"),
    repo: InMemoryInsightRepository = Depends(lambda: default_insight_repository),
) -> List[Dict[str, Any]]:
    """Retrieves filtered risk insights for a conversation."""
    risks = repo.get_risks(conversation_id, priority=priority, category=category)
    return [r.model_dump() for r in risks]


@router.get(
    "/{conversation_id}/insights/opportunities",
    summary="Get Conversation Opportunities with Optional Filters",
    response_model=List[Dict[str, Any]],
)
async def get_conversation_opportunities(
    conversation_id: str,
    priority: Optional[InsightPriority] = Query(None, description="Filter by opportunity priority"),
    category: Optional[InsightCategory] = Query(None, description="Filter by opportunity category"),
    repo: InMemoryInsightRepository = Depends(lambda: default_insight_repository),
) -> List[Dict[str, Any]]:
    """Retrieves filtered opportunity insights for a conversation."""
    opps = repo.get_opportunities(conversation_id, priority=priority, category=category)
    return [o.model_dump() for o in opps]


@router.get(
    "/{conversation_id}/insights/action-items",
    summary="Get Conversation Action Items with Optional Filters",
    response_model=List[Dict[str, Any]],
)
async def get_conversation_action_items(
    conversation_id: str,
    priority: Optional[InsightPriority] = Query(None, description="Filter by action item priority"),
    category: Optional[InsightCategory] = Query(None, description="Filter by action item category"),
    repo: InMemoryInsightRepository = Depends(lambda: default_insight_repository),
) -> List[Dict[str, Any]]:
    """Retrieves filtered action item insights for a conversation."""
    actions = repo.get_action_items(conversation_id, priority=priority, category=category)
    return [a.model_dump() for a in actions]


@router.get(
    "/{conversation_id}/insights/views/{view_name}",
    summary="Render Insight Projection View",
    response_model=Dict[str, Any],
)
async def render_insight_view(
    conversation_id: str,
    view_name: str,
    engine: ConversationInsightEngine = Depends(lambda: default_conversation_insight_engine),
    repo: InMemoryInsightRepository = Depends(lambda: default_insight_repository),
) -> Dict[str, Any]:
    """Renders a specific perspective projection ('executive', 'sales', 'operations', 'audit')."""
    result = repo.get_latest_by_conversation(conversation_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No insight results found for conversation '{conversation_id}'.",
        )
    try:
        return engine.render_view(result, view_name)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
