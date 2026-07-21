import logging
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.commercial.models import Subscription, Invoice, InvoiceStatus, SubscriptionStatus

logger = logging.getLogger("hunteros.commercial")

PLAN_PRICES = {
    "starter_monthly": 299.0,
    "starter_annual": 2990.0,
    "professional_monthly": 999.0,
    "professional_annual": 9990.0,
    "enterprise_annual": 24990.0,
}


class BillingEngine:
    """
    Manages recurring subscriptions and invoice generation.
    Designed to be provider-agnostic so Stripe, Paddle, or manual invoicing can be plugged in.
    """

    @staticmethod
    async def create_subscription(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        license_id: uuid.UUID,
        plan_name: str,
        billing_cycle: str = "annual"
    ) -> Subscription:
        """
        Creates a recurring billing relationship for a workspace.
        """
        amount = PLAN_PRICES.get(f"{plan_name}_{billing_cycle}", 0.0)
        now = datetime.utcnow()
        period_days = 365 if billing_cycle == "annual" else 30

        subscription = Subscription(
            workspace_id=workspace_id,
            license_id=license_id,
            plan_name=plan_name,
            billing_cycle=billing_cycle,
            amount_usd=amount,
            status=SubscriptionStatus.active,
            current_period_start=now,
            current_period_end=now + timedelta(days=period_days),
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        logger.info(f"Created subscription for workspace {workspace_id}: {plan_name} ({billing_cycle})")
        return subscription

    @staticmethod
    async def issue_invoice(db: AsyncSession, subscription: Subscription) -> Invoice:
        """
        Issues a formal invoice for the current billing period.
        """
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{str(subscription.workspace_id)[:8].upper()}"

        invoice = Invoice(
            subscription_id=subscription.id,
            workspace_id=subscription.workspace_id,
            invoice_number=invoice_number,
            amount_usd=subscription.amount_usd,
            status=InvoiceStatus.issued,
            issued_at=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=30),
            line_items=[
                {
                    "description": f"{subscription.plan_name} ({subscription.billing_cycle})",
                    "amount": subscription.amount_usd,
                    "currency": "USD"
                }
            ]
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)
        logger.info(f"Issued invoice {invoice.invoice_number} for ${invoice.amount_usd}")
        return invoice
