from typing import List, Type
from uuid import UUID

from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.bus.interfaces import EventConsumer
from app.domain.followup.crm_sync import sync_followup_sent
from app.domain.followup.sales_memory import record_follow_up_sent
from app.integrations.postgres.database import get_session
from app.utils.logger import get_logger

logger = get_logger(__name__)

class FollowUpExecutedConsumer(EventConsumer):
    """
    Consumes followup.executed events and updates CRM and Sales Memory.
    """
    
    @property
    def name(self) -> str:
        return "followup_executed_consumer"
        
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [UniversalBaseEvent]
        
    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if event.category != EventCategory.FOLLOWUP or event.event_name != "followup.executed":
            return
            
        logger.info("handling_followup_executed", event_id=str(event.id))
        
        customer_id_str = event.metadata.get("customer_id")
        if not customer_id_str:
            return
            
        customer_id = UUID(customer_id_str)
        followup_id = UUID(event.correlation_id)
        workspace_id = event.workspace_id
        channel = event.metadata.get("channel", "unknown")
        provider_message_id = event.metadata.get("provider_message_id")
        reason = event.metadata.get("reason")
        strategy = event.metadata.get("strategy", "friendly_reminder")
        
        # In a real microservices architecture, this consumer might live in the integration or memory domains,
        # but for this enforcement sprint, we keep it here to decouple the background worker from direct calls.
        async with get_session() as session:
            try:
                # Update Sales Memory
                await record_follow_up_sent(
                    session, customer_id, 
                    reason=reason, 
                    strategy=strategy,
                    workspace_id=workspace_id
                )
                
                # Update CRM
                await sync_followup_sent(
                    session, followup_id, customer_id, channel, provider_message_id, workspace_id
                )
                
                # O7 Follow-up Sequence Execution
                # Re-evaluate the customer to schedule the NEXT follow-up in the sequence.
                # decision_engine.evaluate will set the correct future scheduled_for date based on cadence rules.
                from app.domain.followup.service import schedule_followup
                await schedule_followup(session, customer_id, workspace_id=workspace_id)
                
                await session.commit()
            except Exception as e:
                logger.error("followup_executed_consumer_error", error=str(e), exc_info=True)
                await session.rollback()
                raise
