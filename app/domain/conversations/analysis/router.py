"""
HunterOS Engage — Conversation Analysis REST Router (Phase 2.2.1)

Frozen Public Analysis API v1 exposing deterministic conversation intelligence.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.conversations.analysis.engine import (
    ConversationAnalysisEngine,
    default_conversation_analysis_engine,
)
from app.domain.conversations.analysis.models import FactCategory, SummaryType
from app.domain.conversations.analysis.schemas import (
    AnalyzeConversationRequest,
    ConversationAnalysisResponse,
    ConversationMetadataDTO,
    ConversationSegmentDTO,
    ConversationSummaryDTO,
    ExtractedFactDTO,
    TopicAnalysisDTO,
)

router = APIRouter(
    prefix="/conversations/analysis",
    tags=["Conversation Analysis"],
)


def get_analysis_engine() -> ConversationAnalysisEngine:
    return default_conversation_analysis_engine


@router.post(
    "/analyze",
    response_model=ConversationAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze conversation",
    description="Execute deterministic 9-stage pipeline on conversation or message stream.",
)
def analyze_conversation(
    request: AnalyzeConversationRequest,
    engine: ConversationAnalysisEngine = Depends(get_analysis_engine),
) -> Any:
    conv_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
    raw_msgs = [m.model_dump() for m in request.messages]

    result = engine.analyze_conversation(
        conversation_id=conv_id,
        workspace_id=request.workspace_id,
        raw_messages=raw_msgs,
        raw_metadata=request.metadata,
    )
    return result


@router.get(
    "/{conversation_id}",
    response_model=ConversationAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation analysis aggregate",
)
def get_analysis(
    conversation_id: str,
    engine: ConversationAnalysisEngine = Depends(get_analysis_engine),
) -> Any:
    result = engine.get_analysis(conversation_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis for conversation [{conversation_id}] not found.",
        )
    return result


@router.get(
    "/{conversation_id}/summary",
    summary="Get conversation summaries",
)
def get_summary(
    conversation_id: str,
    summary_type: Optional[SummaryType] = Query(None, description="Specific summary perspective"),
    engine: ConversationAnalysisEngine = Depends(get_analysis_engine),
) -> Any:
    summary = engine.get_summary(conversation_id, summary_type=summary_type)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary for conversation [{conversation_id}] not found.",
        )
    return summary


@router.get(
    "/{conversation_id}/topics",
    response_model=TopicAnalysisDTO,
    summary="Get topic analysis and timeline",
)
def get_topics(
    conversation_id: str,
    engine: ConversationAnalysisEngine = Depends(get_analysis_engine),
) -> Any:
    topics = engine.get_topics(conversation_id)
    if not topics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topics for conversation [{conversation_id}] not found.",
        )
    return topics


@router.get(
    "/{conversation_id}/facts",
    response_model=List[ExtractedFactDTO],
    summary="Get extracted facts",
)
def get_facts(
    conversation_id: str,
    category: Optional[FactCategory] = Query(None, description="Filter by fact category"),
    engine: ConversationAnalysisEngine = Depends(get_analysis_engine),
) -> Any:
    facts = engine.get_facts(conversation_id, category=category)
    return facts


@router.get(
    "/{conversation_id}/segments",
    response_model=List[ConversationSegmentDTO],
    summary="Get conversation segments",
)
def get_segments(
    conversation_id: str,
    engine: ConversationAnalysisEngine = Depends(get_analysis_engine),
) -> Any:
    segments = engine.get_segments(conversation_id)
    return segments


@router.get(
    "/{conversation_id}/metadata",
    response_model=ConversationMetadataDTO,
    summary="Get conversation metadata",
)
def get_metadata(
    conversation_id: str,
    engine: ConversationAnalysisEngine = Depends(get_analysis_engine),
) -> Any:
    metadata = engine.get_metadata(conversation_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metadata for conversation [{conversation_id}] not found.",
        )
    return metadata


@router.get(
    "/system/taxonomies",
    summary="List available topic taxonomy paths",
)
def list_taxonomies(
    engine: ConversationAnalysisEngine = Depends(get_analysis_engine),
) -> Any:
    nodes = engine.taxonomy.collect_all_nodes()
    return [
        {
            "name": n.name,
            "path": n.path,
            "category": n.category,
            "keywords": n.keywords,
            "description": n.description,
        }
        for n in nodes
    ]


@router.get(
    "/system/templates",
    summary="List available summary templates",
)
def list_templates(
    engine: ConversationAnalysisEngine = Depends(get_analysis_engine),
) -> Any:
    templates = engine.template_registry.list_templates()
    return [
        {
            "template_name": t.template_name,
            "summary_type": t.summary_type.value,
            "description": t.description,
        }
        for t in templates
    ]
