import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.v1.auth_deps import RequirePermissions, get_current_user
from app.integrations.postgres.database import get_db
from app.domain.commercial.models import (
    License, Subscription, Invoice, SalesPipelineLead,
    Edition, PipelineStage
)
from app.domain.commercial.engines.licensing import LicensingEngine
from app.domain.commercial.engines.billing import BillingEngine
from app.domain.commercial.engines.sales import SalesEngine
from app.domain.commercial.engines.launch import LaunchEngine

router = APIRouter(prefix="/commercial", tags=["Commercial Operations"])


# ── Licensing ──────────────────────────────────────────────────────────────────

class ProvisionLicenseRequest(BaseModel):
    workspace_id: uuid.UUID
    edition: Edition
    trial_days: int = 0

@router.post("/licenses", dependencies=[Depends(RequirePermissions("edit_all"))])
async def provision_license(request: ProvisionLicenseRequest, db: AsyncSession = Depends(get_db)):
    """Provisions a new license for a workspace."""
    license_record = await LicensingEngine.provision_license(
        db, request.workspace_id, request.edition, request.trial_days
    )
    return {"license_id": license_record.id, "edition": license_record.edition, "status": license_record.status}

@router.get("/licenses/{workspace_id}/entitlements", dependencies=[Depends(RequirePermissions("view_all"))])
async def get_entitlements(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Returns the feature entitlements for a workspace."""
    return await LicensingEngine.get_entitlements(db, workspace_id)

@router.put("/licenses/{workspace_id}/upgrade", dependencies=[Depends(RequirePermissions("edit_all"))])
async def upgrade_license(workspace_id: uuid.UUID, edition: Edition, db: AsyncSession = Depends(get_db)):
    """Upgrades a workspace license to a higher edition."""
    return await LicensingEngine.upgrade_license(db, workspace_id, edition)


# ── Subscriptions & Billing ────────────────────────────────────────────────────

class CreateSubscriptionRequest(BaseModel):
    workspace_id: uuid.UUID
    license_id: uuid.UUID
    plan_name: str
    billing_cycle: str = "annual"

@router.post("/subscriptions", dependencies=[Depends(RequirePermissions("edit_all"))])
async def create_subscription(request: CreateSubscriptionRequest, db: AsyncSession = Depends(get_db)):
    """Creates a recurring subscription for a workspace."""
    sub = await BillingEngine.create_subscription(
        db, request.workspace_id, request.license_id, request.plan_name, request.billing_cycle
    )
    invoice = await BillingEngine.issue_invoice(db, sub)
    return {"subscription_id": sub.id, "invoice_number": invoice.invoice_number, "amount_usd": invoice.amount_usd}

@router.get("/billing/invoices", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_invoices(db: AsyncSession = Depends(get_db)):
    """Lists all issued invoices."""
    stmt = select(Invoice).order_by(Invoice.issued_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# ── Sales Pipeline ─────────────────────────────────────────────────────────────

class CreateLeadRequest(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    estimated_arr_usd: Optional[float] = None

class AdvanceStageRequest(BaseModel):
    new_stage: PipelineStage
    win_probability: Optional[float] = None
    note: Optional[str] = None

@router.post("/sales/leads", dependencies=[Depends(RequirePermissions("edit_all"))])
async def create_lead(request: CreateLeadRequest, db: AsyncSession = Depends(get_db)):
    """Adds a new lead to the sales pipeline."""
    return await SalesEngine.create_lead(db, request.company_name, request.contact_name, request.estimated_arr_usd)

@router.put("/sales/leads/{lead_id}/stage", dependencies=[Depends(RequirePermissions("edit_all"))])
async def advance_lead_stage(lead_id: uuid.UUID, request: AdvanceStageRequest, db: AsyncSession = Depends(get_db)):
    """Advances a sales lead to the next pipeline stage."""
    return await SalesEngine.advance_stage(db, lead_id, request.new_stage, request.win_probability, request.note)

@router.get("/sales/pipeline", dependencies=[Depends(RequirePermissions("view_all"))])
async def get_pipeline_summary(db: AsyncSession = Depends(get_db)):
    """Returns the pipeline summary rollup for the leadership dashboard."""
    return await SalesEngine.get_pipeline_summary(db)


# ── Leadership Dashboard ───────────────────────────────────────────────────────

@router.get("/dashboard", dependencies=[Depends(RequirePermissions("view_all"))])
async def get_commercial_dashboard(db: AsyncSession = Depends(get_db)):
    """Returns the aggregated Commercial Business Operations Dashboard."""
    return await LaunchEngine.get_commercial_dashboard(db)

@router.get("/launch-readiness", dependencies=[Depends(RequirePermissions("view_all"))])
async def get_launch_readiness():
    """Returns the Phase 10 launch readiness checklist across all operational areas."""
    return LaunchEngine.get_launch_readiness()
