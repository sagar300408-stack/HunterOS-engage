from typing import List
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.v1.auth_deps import RequirePermissions, get_current_user
from app.integrations.postgres.database import get_db

from app.domain.customer_success.models import CustomerLifecycle, SupportTicket, LifecycleStage
from app.domain.customer_success.engines.lifecycle import LifecycleEngine
from app.domain.customer_success.engines.reviews import ExecutiveReviewEngine
from app.domain.customer_success.engines.support import SupportEngine

router = APIRouter(prefix="/customers", tags=["Customer Success"])

# ── Lifecycle ─────────────────────────────────────────────────────────────────

@router.get("", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_customers(db: AsyncSession = Depends(get_db)):
    """List all customers and their lifecycle stages."""
    stmt = select(CustomerLifecycle)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/{workspace_id}/stage", dependencies=[Depends(RequirePermissions("edit_all"))])
async def advance_stage(workspace_id: uuid.UUID, stage: LifecycleStage, db: AsyncSession = Depends(get_db)):
    """Manually advance a customer's lifecycle stage."""
    return await LifecycleEngine.advance_stage(db, workspace_id, stage)


# ── Executive Reviews ─────────────────────────────────────────────────────────

@router.post("/{workspace_id}/executive-review", dependencies=[Depends(RequirePermissions("edit_all"))])
async def generate_ebr(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Generates an Executive Business Review (EBR)."""
    return await ExecutiveReviewEngine.generate_ebr(db, workspace_id)


# ── Support ───────────────────────────────────────────────────────────────────

support_router = APIRouter(prefix="/support", tags=["Customer Support"])

class TicketRequest(BaseModel):
    subject: str
    description: str

@support_router.post("/tickets")
async def create_ticket(request: TicketRequest, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """Open a new enterprise support ticket."""
    return await SupportEngine.open_ticket(
        db, current_user.workspace_id, current_user.id, request.subject, request.description
    )

@support_router.get("/tickets", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_tickets(db: AsyncSession = Depends(get_db)):
    """List open support tickets."""
    stmt = select(SupportTicket).order_by(SupportTicket.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
