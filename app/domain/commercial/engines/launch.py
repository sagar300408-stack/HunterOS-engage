from datetime import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.domain.commercial.models import License, LicenseStatus, Subscription, Invoice, SalesPipelineLead, PipelineStage
from app.domain.analytics.models import CustomerHealthSnapshot

import logging
logger = logging.getLogger("hunteros.commercial")

# Launch Readiness Areas: each area has a name and a list of acceptance criteria with status.
LAUNCH_CHECKLIST: Dict[str, Any] = {
    "Product": [
        {"criterion": "Production-ready infrastructure deployed", "status": "complete"},
        {"criterion": "Security validation complete (Milestone 10.2)", "status": "complete"},
        {"criterion": "Documentation published", "status": "complete"},
        {"criterion": "Performance benchmarks passing", "status": "complete"},
    ],
    "Engineering": [
        {"criterion": "Observability and monitoring active", "status": "complete"},
        {"criterion": "Deployment automation configured", "status": "complete"},
        {"criterion": "Reliability and chaos testing complete", "status": "complete"},
    ],
    "Sales": [
        {"criterion": "Pricing finalized", "status": "complete"},
        {"criterion": "Demo environment ready", "status": "complete"},
        {"criterion": "Sales playbooks complete", "status": "complete"},
        {"criterion": "Licensing engine active", "status": "complete"},
    ],
    "Marketing": [
        {"criterion": "Website live", "status": "pending"},
        {"criterion": "Case studies published", "status": "pending"},
        {"criterion": "Product videos produced", "status": "pending"},
        {"criterion": "Launch campaign scheduled", "status": "pending"},
    ],
    "Customer Success": [
        {"criterion": "Onboarding playbooks defined", "status": "complete"},
        {"criterion": "Support ticketing active", "status": "complete"},
        {"criterion": "Executive Business Review process established", "status": "complete"},
    ],
    "Legal": [
        {"criterion": "Terms of Service ready", "status": "pending"},
        {"criterion": "Privacy Policy ready", "status": "pending"},
        {"criterion": "Data Processing Agreement (DPA) ready", "status": "pending"},
        {"criterion": "SLA document ready", "status": "pending"},
    ],
    "Finance": [
        {"criterion": "Billing system active", "status": "complete"},
        {"criterion": "Subscription management active", "status": "complete"},
        {"criterion": "Invoice generation active", "status": "complete"},
    ],
    "Leadership": [
        {"criterion": "Business dashboards operational", "status": "complete"},
        {"criterion": "KPIs and forecasting established", "status": "complete"},
    ],
}


class LaunchEngine:
    """
    Coordinates commercial launch readiness and generates leadership business dashboards.
    """

    @staticmethod
    def get_launch_readiness() -> Dict[str, Any]:
        """
        Returns the official launch readiness checklist across all operational areas.
        """
        summary = {}
        total = 0
        complete = 0

        for area, items in LAUNCH_CHECKLIST.items():
            area_total = len(items)
            area_complete = sum(1 for i in items if i["status"] == "complete")
            pct = round((area_complete / area_total) * 100) if area_total > 0 else 0
            summary[area] = {
                "progress": f"{area_complete}/{area_total}",
                "percentage": pct,
                "items": items,
                "ready": pct == 100,
            }
            total += area_total
            complete += area_complete

        return {
            "overall_readiness": round((complete / total) * 100) if total > 0 else 0,
            "areas": summary,
            "assessed_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    async def get_commercial_dashboard(db: AsyncSession) -> Dict[str, Any]:
        """
        Aggregates live commercial metrics for the leadership Business Operations Dashboard.
        """
        # Active licenses
        active_license_count = await db.scalar(
            select(func.count(License.id)).where(License.status == LicenseStatus.active)
        ) or 0

        # Total ARR from active subscriptions
        total_arr = await db.scalar(
            select(func.sum(Subscription.amount_usd)).where(Subscription.status == "active")
        ) or 0.0

        # Open invoices
        open_invoice_count = await db.scalar(
            select(func.count(Invoice.id)).where(Invoice.status == "issued")
        ) or 0

        # Pipeline value
        pipeline_value = await db.scalar(
            select(func.sum(SalesPipelineLead.estimated_arr_usd)).where(
                SalesPipelineLead.stage.notin_([PipelineStage.closed_won, PipelineStage.closed_lost])
            )
        ) or 0.0

        # Customer health distribution
        health_stmt = select(
            func.avg(CustomerHealthSnapshot.health_score),
            func.count(CustomerHealthSnapshot.id)
        )
        health_result = await db.execute(health_stmt)
        avg_health, health_count = health_result.one_or_none() or (0.0, 0)

        return {
            "revenue": {
                "active_customers": active_license_count,
                "total_arr_usd": total_arr,
                "open_invoices": open_invoice_count,
            },
            "sales": {
                "pipeline_value_usd": pipeline_value,
            },
            "customers": {
                "average_health_score": round(avg_health or 0.0, 1),
                "health_snapshots_count": health_count,
            },
            "launch_readiness": LaunchEngine.get_launch_readiness()["overall_readiness"],
            "generated_at": datetime.utcnow().isoformat(),
        }
