import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.integrations.postgres.database import get_db
from app.domain.context.schemas import (
    CustomerContextSchema,
    BusinessOntologySchema,
    ContextDashboardSummary
)
from app.domain.context.repository import ContextRepository

router = APIRouter(prefix="/context", tags=["Context"])

@router.get("/organization")
async def get_organization(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return {"message": "Organization context retrieved"}

@router.get("/customers", response_model=List[CustomerContextSchema])
async def get_customers(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Placeholder
    return []
    
@router.get("/ontology", response_model=List[BusinessOntologySchema])
async def get_ontology(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Placeholder
    return []

@router.get("/quality-dashboard", response_model=ContextDashboardSummary)
async def get_quality_dashboard(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns the executive context quality metrics computed from real DB data.

    Computes:
      - stale_records: count of CustomerContext entities whose last_verified_at
        exceeds their stale_threshold_days
      - average_freshness_days: mean days since last_verified_at across all
        active CustomerContext entities (0.0 if none)
      - conflicts: count of unresolved ContextConflict rows for this workspace
      - knowledge_completeness: percentage of active entities that are NOT stale
      - missing_relationships: active entities with no outgoing KnowledgeGraphEdge
      - ontology_coverage: placeholder 100.0 until full gap analysis is implemented
    """
    from sqlalchemy.future import select
    from app.domain.context.models import CustomerContext, KnowledgeGraphEdge
    from app.domain.context.engines.freshness import ContextFreshnessEngine

    repo = ContextRepository(db)

    # ── Real: unresolved conflicts ────────────────────────────────────────────
    conflicts = await repo.list_unresolved_conflicts(workspace_id)
    conflict_count = len(conflicts)

    # ── Real: stale record evaluation across CustomerContext entities ─────────
    result = await db.execute(
        select(CustomerContext).where(
            CustomerContext.workspace_id == workspace_id,
            CustomerContext.is_active == True,
        )
    )
    entities = result.scalars().all()

    total_entities = len(entities)
    stale_count = 0
    total_freshness_days = 0.0

    for entity in entities:
        is_stale, days_since = ContextFreshnessEngine.evaluate(entity)
        if is_stale:
            stale_count += 1
        total_freshness_days += days_since

    average_freshness_days = (
        round(total_freshness_days / total_entities, 1)
        if total_entities > 0
        else 0.0
    )

    knowledge_completeness = (
        round(((total_entities - stale_count) / total_entities) * 100.0, 1)
        if total_entities > 0
        else 100.0  # no entities → nothing stale → completeness is 100%
    )

    # ── Real: entities with no outgoing KnowledgeGraphEdge ───────────────────
    edge_result = await db.execute(
        select(KnowledgeGraphEdge.source_entity_id).where(
            KnowledgeGraphEdge.workspace_id == workspace_id
        ).distinct()
    )
    connected_ids = {row[0] for row in edge_result.all()}
    entity_ids = {e.id for e in entities}
    missing_relationships = len(entity_ids - connected_ids)

    return ContextDashboardSummary(
        knowledge_completeness=knowledge_completeness,
        stale_records=stale_count,
        conflicts=conflict_count,
        missing_relationships=missing_relationships,
        ontology_coverage=100.0,   # full ontology analysis is a future milestone
        average_freshness_days=average_freshness_days,
    )

@router.post("/sync")
async def sync_providers(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Triggers the ContextProviderInterface across configured external systems."""
    return {"status": "Sync initiated"}
