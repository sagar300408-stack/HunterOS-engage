"""
HunterOS Engage V1 - Intent Intelligence FastAPI Router
REST endpoints for executing intent detection, fetching views, and querying taxonomy.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.domain.intents.api import intent_api_v1
from app.domain.intents.models import (
    BusinessImportance,
    IntentTaxonomyCategory,
    IntentType,
)
from app.domain.intents.rules.registry import default_rule_pack_registry
from app.domain.intents.schemas import (
    DetectedIntentDTO,
    IntentDetectionResultDTO,
)

router = APIRouter(prefix="/api/v1/intents", tags=["Intent Intelligence"])

from app.domain.intents.classification.router import router as classification_router
router.include_router(classification_router)

from app.domain.intents.evolution.router import router as evolution_router
router.include_router(evolution_router)


@router.get(
    "/taxonomy",
    summary="Get Intent Taxonomy Tree",
    response_model=Dict[str, Any],
)
def get_taxonomy() -> Dict[str, Any]:
    """Returns the complete hierarchical Intent Taxonomy tree."""
    return intent_api_v1.get_taxonomy_tree()


@router.get(
    "/rules/packs",
    summary="List Registered Rule Packs",
    response_model=List[Dict[str, Any]],
)
def list_rule_packs() -> List[Dict[str, Any]]:
    """List all registered modular rule packs and their rules."""
    packs = default_rule_pack_registry.list_packs()
    return [
        {
            "pack_name": p.pack_name,
            "pack_version": p.pack_version,
            "description": p.description,
            "rules": [
                {
                    "rule_name": r.rule_name,
                    "rule_version": r.rule_version,
                    "target_intents": [t.value for t in r.target_intent_types],
                }
                for r in p.get_rules()
            ],
        }
        for p in packs
    ]


@router.get(
    "/{conversation_id}",
    summary="Get Detected Intents for Conversation",
    response_model=IntentDetectionResultDTO,
)
def get_conversation_intents(conversation_id: str) -> Any:
    """Retrieve full Intent Detection Result for a given conversation ID."""
    result = intent_api_v1.get_conversation_intents(conversation_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No detected intents found for conversation '{conversation_id}'.",
        )
    return result.to_dict()


@router.get(
    "/{conversation_id}/views/{view_name}",
    summary="Render Perspective View",
    response_model=Dict[str, Any],
)
def render_perspective_view(conversation_id: str, view_name: str) -> Dict[str, Any]:
    """Render perspective projection (executive, sales, operations, audit)."""
    try:
        view_data = intent_api_v1.render_view(conversation_id, view_name)
        if not view_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No detected intents found for conversation '{conversation_id}'.",
            )
        return view_data
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )


@router.get(
    "/{conversation_id}/evidence-graph",
    summary="Get Combined Evidence Graph",
    response_model=Dict[str, Any],
)
def get_evidence_graph(conversation_id: str) -> Dict[str, Any]:
    """Retrieve combined evidence graph of all detected intents for a conversation."""
    result = intent_api_v1.get_conversation_intents(conversation_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No detected intents found for conversation '{conversation_id}'.",
        )

    all_nodes: List[Dict[str, Any]] = []
    all_edges: List[Dict[str, Any]] = []
    seen_nodes = set()

    for intent in result.intents:
        g = intent.supporting_evidence.evidence_graph
        if g:
            for node in g.nodes:
                if node.node_id not in seen_nodes:
                    seen_nodes.add(node.node_id)
                    all_nodes.append(node.to_dict())
            for edge in g.edges:
                all_edges.append(edge.to_dict())

    return {
        "conversation_id": conversation_id,
        "total_nodes": len(all_nodes),
        "total_edges": len(all_edges),
        "nodes": all_nodes,
        "edges": all_edges,
    }


@router.get(
    "",
    summary="Query Detected Intents",
    response_model=List[DetectedIntentDTO],
)
def query_intents(
    conversation_id: Optional[str] = None,
    workspace_id: Optional[uuid.UUID] = None,
    intent_type: Optional[IntentType] = None,
    category: Optional[IntentTaxonomyCategory] = None,
    importance: Optional[BusinessImportance] = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=1000),
) -> Any:
    """Query across all detected intents matching criteria."""
    intents = intent_api_v1.query_intents(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        intent_type=intent_type,
        category=category,
        importance=importance,
        min_confidence=min_confidence,
        limit=limit,
    )
    return [i.to_dict() for i in intents]
