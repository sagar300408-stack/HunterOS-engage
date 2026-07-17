from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.autonomous.schemas import (
    OperationalOpportunitySchema, ExecutionPlanSchema, 
    ExecutePlanRequest, CancelPlanRequest
)
from app.domain.autonomous.engine import AutonomousOperationsEngine

router = APIRouter(prefix="/autonomous", tags=["autonomous"])


def get_autonomous_engine(request: Request, db: AsyncSession = Depends(get_db)) -> AutonomousOperationsEngine:
    return AutonomousOperationsEngine(session=db, event_bus=request.app.state.event_bus)


@router.get("/opportunities", response_model=List[OperationalOpportunitySchema])
async def list_opportunities(
    workspace_id: UUID,
    engine: AutonomousOperationsEngine = Depends(get_autonomous_engine)
):
    return await engine.list_opportunities(workspace_id)


@router.get("/plans", response_model=List[ExecutionPlanSchema])
async def list_plans(
    workspace_id: UUID,
    engine: AutonomousOperationsEngine = Depends(get_autonomous_engine)
):
    return await engine.list_plans(workspace_id)


@router.post("/plans/{plan_id}/execute", response_model=ExecutionPlanSchema)
async def execute_plan(
    plan_id: UUID,
    req: ExecutePlanRequest,
    engine: AutonomousOperationsEngine = Depends(get_autonomous_engine)
):
    try:
        return await engine.execute_plan(plan_id, req.idempotency_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plans/{plan_id}/cancel", response_model=ExecutionPlanSchema)
async def cancel_plan(
    plan_id: UUID,
    req: CancelPlanRequest,
    engine: AutonomousOperationsEngine = Depends(get_autonomous_engine)
):
    try:
        return await engine.cancel_plan(plan_id, req.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
