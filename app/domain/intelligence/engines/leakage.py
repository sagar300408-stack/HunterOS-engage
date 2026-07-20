import uuid
from typing import List
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.intelligence.models import OpportunityLeakageEvent
from app.domain.customers.models import Customer, CustomerStatus


class OpportunityLeakageEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        # Average Deal Size as a fallback (could be fetched from a WorkspaceSettings model)
        self.AVG_DEAL_SIZE_INR = 250000.0 

    async def scan_leakages(self, workspace_id: uuid.UUID) -> List[OpportunityLeakageEvent]:
        """
        Scans for dropped or ghosted customers and generates leakage events.
        """
        now = datetime.now(timezone.utc)
        ghosting_threshold = now - timedelta(days=14)

        # Find lost leads and ghosted customers
        result = await self.session.execute(
            select(Customer)
            .where(
                and_(
                    Customer.workspace_id == workspace_id,
                    or_(
                        Customer.status == CustomerStatus.inactive.value,
                        and_(
                            Customer.status == CustomerStatus.active.value,
                            Customer.last_interaction < ghosting_threshold
                        )
                    )
                )
            )
        )
        customers = result.scalars().all()

        leakages = []
        for cust in customers:
            if cust.status == CustomerStatus.inactive.value:
                leakage_type = "LOST_LEAD"
                description = f"Lead {cust.name} was marked as inactive."
            else:
                leakage_type = "GHOSTED_CUSTOMER"
                days_idle = (now - (cust.last_interaction or cust.created_at)).days
                description = f"Lead {cust.name} has ghosted. No interaction for {days_idle} days."

            # Calculate value (if the customer model had a potential_value field we'd use it)
            revenue_at_risk = self.AVG_DEAL_SIZE_INR

            # Check if this leakage already exists
            existing_result = await self.session.execute(
                select(OpportunityLeakageEvent)
                .where(
                    OpportunityLeakageEvent.workspace_id == workspace_id,
                    OpportunityLeakageEvent.source_entity_id == cust.id,
                    OpportunityLeakageEvent.leakage_type == leakage_type
                )
            )
            existing = existing_result.scalars().first()

            if not existing:
                leakage = OpportunityLeakageEvent(
                    workspace_id=workspace_id,
                    leakage_type=leakage_type,
                    revenue_at_risk=revenue_at_risk,
                    currency="INR",
                    source_entity_type="customer",
                    source_entity_id=cust.id,
                    description=description,
                    detected_at=now
                )
                self.session.add(leakage)
                leakages.append(leakage)

        # Note: We do not flush here, the pipeline orchestrator will commit/flush.
        return leakages
