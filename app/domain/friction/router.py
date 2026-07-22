"""
Business Friction Engine — REST API
─────────────────────────────────────
Endpoints:
  GET  /friction/score/{workspace_id}            Current BFS + contributors + trend
  GET  /friction/score/{workspace_id}/history    Time-series BFS data (last N days)
  GET  /friction/events/{workspace_id}           All detected friction events
  GET  /friction/events/{workspace_id}/open      Open (unresolved) friction events
  GET  /friction/summary/{workspace_id}          Executive dashboard payload
  GET  /friction/bottlenecks/{workspace_id}      Workflow stage latency table
  GET  /friction/sla/{workspace_id}              SLA policies list
  POST /friction/sla/{workspace_id}              Create a new SLA policy
  GET  /friction/recommendations/{workspace_id}  Friction-based recommendations
  POST /friction/analyze/{workspace_id}          Trigger on-demand full scan
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.friction.analyzer import BusinessFrictionAnalyzer
from app.domain.friction.models import SLAPolicy
from app.domain.friction.repository import FrictionRepository
from app.domain.friction.schemas import (
    AnalysisTriggerResponse,
    FrictionEventResponse,
    FrictionScoreHistoryItem,
    FrictionScoreResponse,
    FrictionSummaryResponse,
    SLAComplianceResponse,
    SLAPolicyCreate,
    SLAPolicyResponse,
    TopFrictionSource,
    WorkflowLatencyResponse,
)
from app.domain.security.models import DEFAULT_WORKSPACE_ID

router = APIRouter(prefix="/friction", tags=["Business Friction Engine"])

_FRICTION_TYPE_LABELS = {
    "LEAD_RESPONSE_DELAY": "Lead Response Delays",
    "MISSED_FOLLOWUP":     "Missed Follow-ups",
    "SLA_VIOLATION":       "SLA Violations",
    "APPROVAL_DELAY":      "Approval Bottlenecks",
    "WORKFLOW_STALL":      "Workflow Stalls",
    "CUSTOMER_INACTIVITY": "Customer Inactivity",
    "OPPORTUNITY_LEAKAGE": "Opportunity Leakage",
}


def _repo(session: AsyncSession = Depends(get_db)) -> FrictionRepository:
    return FrictionRepository(session)


# ── Score endpoints ───────────────────────────────────────────────────────────

@router.get(
    "/score/{workspace_id}",
    response_model=FrictionScoreResponse,
    summary="Get current Business Friction Score",
)
async def get_friction_score(
    workspace_id: UUID,
    repo: FrictionRepository = Depends(_repo),
):
    snapshot = await repo.get_latest_score(workspace_id)
    if not snapshot:
        # Return a zero-score if never computed
        return FrictionScoreResponse(
            workspace_id=workspace_id,
            score=0.0,
            previous_score=None,
            score_delta=None,
            trend="STABLE",
            contributors={},
            calculated_at=datetime.now(timezone.utc),
        )
    return FrictionScoreResponse(
        workspace_id=snapshot.workspace_id,
        score=snapshot.score,
        previous_score=snapshot.previous_score,
        score_delta=snapshot.score_delta,
        trend=snapshot.trend,
        contributors=snapshot.contributors or {},
        calculated_at=snapshot.calculated_at,
    )


@router.get(
    "/score/{workspace_id}/history",
    response_model=List[FrictionScoreHistoryItem],
    summary="Get Business Friction Score history",
)
async def get_friction_score_history(
    workspace_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    repo: FrictionRepository = Depends(_repo),
):
    snapshots = await repo.get_score_history(workspace_id, days)
    return [
        FrictionScoreHistoryItem(
            score=s.score,
            trend=s.trend,
            calculated_at=s.calculated_at,
        )
        for s in snapshots
    ]


# ── Friction Events ───────────────────────────────────────────────────────────

@router.get(
    "/events/{workspace_id}",
    response_model=List[FrictionEventResponse],
    summary="List all friction events",
)
async def get_friction_events(
    workspace_id: UUID,
    friction_type: Optional[str] = Query(default=None),
    severity: Optional[str]      = Query(default=None),
    limit: int                   = Query(default=50, le=200),
    repo: FrictionRepository = Depends(_repo),
):
    events = await repo.get_friction_events(
        workspace_id=workspace_id,
        friction_type=friction_type,
        severity=severity,
        limit=limit,
    )
    return [FrictionEventResponse.model_validate(e) for e in events]


@router.get(
    "/events/{workspace_id}/open",
    response_model=List[FrictionEventResponse],
    summary="List open (unresolved) friction events",
)
async def get_open_friction_events(
    workspace_id: UUID,
    repo: FrictionRepository = Depends(_repo),
):
    events = await repo.get_open_friction_events(workspace_id)
    return [FrictionEventResponse.model_validate(e) for e in events]


# ── Executive Summary ─────────────────────────────────────────────────────────

@router.get(
    "/summary/{workspace_id}",
    response_model=FrictionSummaryResponse,
    summary="Executive friction dashboard summary",
)
async def get_friction_summary(
    workspace_id: UUID,
    repo: FrictionRepository = Depends(_repo),
):
    snapshot    = await repo.get_latest_score(workspace_id)
    open_count  = await repo.count_open_events(workspace_id)
    crit_count  = await repo.count_critical_events(workspace_id)
    bottlenecks = await repo.get_bottleneck_stages(workspace_id)
    open_by_type = await repo.get_open_events_by_type(workspace_id)

    score      = snapshot.score if snapshot else 0.0
    trend      = snapshot.trend if snapshot else "STABLE"
    delta      = snapshot.score_delta if snapshot else None
    contribs   = (snapshot.contributors or {}) if snapshot else {}

    # Build top 5 friction sources
    top_sources = []
    for ftype, contribution in sorted(contribs.items(), key=lambda x: x[1], reverse=True)[:5]:
        top_sources.append(TopFrictionSource(
            friction_type=ftype,
            contribution=contribution,
            open_count=open_by_type.get(ftype, 0),
            description=_FRICTION_TYPE_LABELS.get(ftype, ftype),
        ))

    # SLA compliance (rough estimate from SLA_VIOLATION events)
    sla_violations = open_by_type.get("SLA_VIOLATION", 0)
    sla_compliance = max(0.0, round(100.0 - (sla_violations * 5.0), 1))

    bottleneck_responses = [
        WorkflowLatencyResponse(
            id=b.id,
            workspace_id=b.workspace_id,
            stage_name=b.stage_name,
            expected_duration_hours=b.expected_duration_hours,
            actual_avg_hours=b.actual_avg_hours,
            sample_count=b.sample_count,
            status=b.status,
            delay_factor=round(b.actual_avg_hours / max(b.expected_duration_hours, 0.001), 2),
            last_updated=b.last_updated,
        )
        for b in bottlenecks
    ]

    return FrictionSummaryResponse(
        workspace_id=workspace_id,
        business_friction_score=score,
        score_trend=trend,
        score_delta=delta,
        top_friction_sources=top_sources,
        open_friction_events=open_count,
        critical_events=crit_count,
        sla_compliance_pct=sla_compliance,
        bottleneck_stages=bottleneck_responses,
        generated_at=datetime.now(timezone.utc),
    )


# ── Workflow Bottlenecks ──────────────────────────────────────────────────────

@router.get(
    "/bottlenecks/{workspace_id}",
    response_model=List[WorkflowLatencyResponse],
    summary="Workflow stage latency report",
)
async def get_bottlenecks(
    workspace_id: UUID,
    repo: FrictionRepository = Depends(_repo),
):
    stages = await repo.get_workflow_latency(workspace_id)
    return [
        WorkflowLatencyResponse(
            id=s.id,
            workspace_id=s.workspace_id,
            stage_name=s.stage_name,
            expected_duration_hours=s.expected_duration_hours,
            actual_avg_hours=s.actual_avg_hours,
            sample_count=s.sample_count,
            status=s.status,
            delay_factor=round(s.actual_avg_hours / max(s.expected_duration_hours, 0.001), 2),
            last_updated=s.last_updated,
        )
        for s in stages
    ]


# ── SLA Policies ──────────────────────────────────────────────────────────────

@router.get(
    "/sla/{workspace_id}",
    response_model=List[SLAPolicyResponse],
    summary="List SLA policies for a workspace",
)
async def get_sla_policies(
    workspace_id: UUID,
    repo: FrictionRepository = Depends(_repo),
):
    policies = await repo.get_sla_policies(workspace_id, active_only=False)
    return [SLAPolicyResponse.model_validate(p) for p in policies]


@router.post(
    "/sla/{workspace_id}",
    response_model=SLAPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new SLA policy",
)
async def create_sla_policy(
    workspace_id: UUID,
    body: SLAPolicyCreate,
    repo: FrictionRepository = Depends(_repo),
    session: AsyncSession = Depends(get_db),
):
    policy = SLAPolicy(
        workspace_id=workspace_id,
        policy_name=body.policy_name,
        event_trigger=body.event_trigger,
        target_metric=body.target_metric,
        description=body.description,
        warning_threshold_minutes=body.warning_threshold_minutes,
        critical_threshold_minutes=body.critical_threshold_minutes,
        is_active=body.is_active,
    )
    saved = await repo.save_sla_policy(policy)
    await session.commit()
    return SLAPolicyResponse.model_validate(saved)


# ── Recommendations ───────────────────────────────────────────────────────────

@router.get(
    "/recommendations/{workspace_id}",
    summary="Friction-based recommendations",
)
async def get_friction_recommendations(
    workspace_id: UUID,
    limit: int = Query(default=10, le=50),
    session: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, desc
    from app.domain.recommendation.models import (
        RecommendationSnapshot, RecommendationLifecycle
    )
    result = await session.execute(
        select(RecommendationSnapshot)
        .where(
            RecommendationSnapshot.workspace_id == workspace_id,
            RecommendationSnapshot.generator_name == "FrictionRecommendationEngine",
            RecommendationSnapshot.lifecycle_status == RecommendationLifecycle.ACTIVE.value,
        )
        .order_by(desc(RecommendationSnapshot.recommendation_score))
        .limit(limit)
    )
    recs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "summary": r.summary,
            "category": r.category,
            "priority": r.priority,
            "risk_level": r.risk_level,
            "recommendation_score": r.recommendation_score,
            "confidence": r.confidence,
            "suggested_actions": r.suggested_actions,
            "decision_trace": r.decision_trace,
            "generated_at": r.generated_at,
        }
        for r in recs
    ]


# ── On-demand Analysis ────────────────────────────────────────────────────────

@router.post(
    "/analyze/{workspace_id}",
    response_model=AnalysisTriggerResponse,
    summary="Trigger on-demand friction analysis",
)
async def trigger_analysis(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    try:
        analyzer = BusinessFrictionAnalyzer(session)
        result   = await analyzer.run_full_scan(workspace_id)
        await session.commit()
        return AnalysisTriggerResponse(
            workspace_id=workspace_id,
            friction_events_detected=result["friction_events_detected"],
            new_score=result["new_score"],
            previous_score=result.get("previous_score"),
            triggered_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
