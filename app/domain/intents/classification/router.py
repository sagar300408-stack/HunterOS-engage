"""
HunterOS Engage V1 - Intent Classification REST Router
FastAPI endpoints for Intent Classification, Taxonomy Graph, Analytics, and Multi-Perspective Views.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, HTTPException, Query, status

from app.domain.intents.api import intent_api_v1
from app.domain.intents.classification.api import canonical_intent_api_v1
from app.domain.intents.classification.schemas import (
    ClassifiedIntentDTO,
    ClassifyIntentsRequest,
    IntentAnalyticsQueryDTO,
    IntentClassificationResultDTO,
    IntentGroupDTO,
    IntentRelationshipDTO,
)

router = APIRouter(prefix="/classification", tags=["Intent Classification"])


@router.post(
    "/classify",
    response_model=IntentClassificationResultDTO,
    status_code=status.HTTP_200_OK,
    summary="Classify intents for a conversation",
)
def classify_conversation_intents(request: ClassifyIntentsRequest) -> Any:
    """
    Executes the 8-stage Intent Classification Pipeline for a conversation.
    """
    # Fetch detection result if available from the detection context
    detection_res = intent_api_v1.get_conversation_intents(request.conversation_id)

    result = canonical_intent_api_v1.classify_conversation(
        conversation_id=request.conversation_id,
        detection_result=detection_res,
        workspace_id=request.workspace_id,
        customer_id=request.customer_id,
        active_plugins=request.active_plugins,
    )
    return result.to_dict()


@router.get(
    "/{classification_id}",
    response_model=IntentClassificationResultDTO,
    summary="Get classification result by ID",
)
def get_classification_by_id(classification_id: uuid.UUID) -> Any:
    res = canonical_intent_api_v1.get_classification(classification_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Classification result '{classification_id}' not found.",
        )
    return res.to_dict()


@router.get(
    "/conversation/{conversation_id}",
    response_model=IntentClassificationResultDTO,
    summary="Get latest classification result for a conversation",
)
def get_latest_conversation_classification(conversation_id: str) -> Any:
    res = canonical_intent_api_v1.get_latest_classification_for_conversation(conversation_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No classification result found for conversation '{conversation_id}'.",
        )
    return res.to_dict()


@router.get(
    "/conversation/{conversation_id}/intents",
    response_model=List[ClassifiedIntentDTO],
    summary="Get classified intents for a conversation",
)
def get_conversation_intents(conversation_id: str) -> Any:
    intents = canonical_intent_api_v1.get_classified_intents_for_conversation(conversation_id)
    return [i.to_dict() for i in intents]


@router.get(
    "/conversation/{conversation_id}/relationships",
    response_model=List[IntentRelationshipDTO],
    summary="Get intent relationships for a conversation",
)
def get_conversation_relationships(conversation_id: str) -> Any:
    rels = canonical_intent_api_v1.get_intent_relationships_for_conversation(conversation_id)
    return [r.to_dict() for r in rels]


@router.get(
    "/conversation/{conversation_id}/groups",
    response_model=List[IntentGroupDTO],
    summary="Get intent groups for a conversation",
)
def get_conversation_groups(conversation_id: str) -> Any:
    groups = canonical_intent_api_v1.get_intent_groups_for_conversation(conversation_id)
    return [g.to_dict() for g in groups]


@router.get(
    "/conversation/{conversation_id}/views/{view_type}",
    summary="Get a projection view (executive, sales, operations, audit)",
)
def get_conversation_view(conversation_id: str, view_type: str) -> Dict[str, Any]:
    try:
        view = canonical_intent_api_v1.get_view(conversation_id, view_type)
        if view is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No classification found for conversation '{conversation_id}'.",
            )
        return view
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/taxonomy/graph",
    summary="Export the business intent taxonomy graph topology",
)
def get_taxonomy_graph_topology() -> Dict[str, Any]:
    return canonical_intent_api_v1.get_taxonomy_graph().export_graph()


@router.get(
    "/processes/list",
    summary="List all registered business processes",
)
def list_business_processes() -> List[Dict[str, Any]]:
    procs = canonical_intent_api_v1.get_process_registry().list_all()
    return [p.to_dict() for p in procs]


@router.get(
    "/plugins/list",
    summary="List all registered industry plugins",
)
def list_industry_plugins() -> List[Dict[str, Any]]:
    plugins = canonical_intent_api_v1.get_plugin_registry().list_plugins()
    return [p.to_dict() for p in plugins]


@router.get(
    "/analytics/summary",
    response_model=IntentAnalyticsQueryDTO,
    summary="Get descriptive classification analytics summary",
)
def get_analytics_summary(workspace_id: Optional[uuid.UUID] = Query(None)) -> Any:
    return canonical_intent_api_v1.run_analytics(workspace_id=workspace_id)
