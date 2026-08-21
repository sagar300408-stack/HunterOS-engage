from app.events.bus.interfaces import EventConsumer
from app.events.model.base_event import UniversalBaseEvent
from typing import List
from app.integrations.postgres.database import get_session
from app.integrations.websocket.manager import ws_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

class UIEventConsumer(EventConsumer):
    """
    Listens for business events on the EventBus and translates them into
    safe UI DTOs for real-time WebSocket delivery, strictly scoped by workspace.
    """
    
    @property
    def name(self) -> str:
        return "ui_experience_consumer"

    def get_subscriptions(self) -> List[type[UniversalBaseEvent]]:
        return [UniversalBaseEvent]

    def get_priority(self) -> int:
        return 1000 # Run last, purely for presentation/analytics updates

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not event.workspace_id:
            return

        # Map backend domain events to the exact UI events the frontend expects
        # Frontend hooks (useWebSocket.ts) listen for:
        # conversation_updated, intent_extracted, customer_updated, lead_stage_changed
        
        ui_event = None
        ui_data = {}

        if event.event_name == "message_received" or event.event_name == "message_sent":
            ui_event = "conversation_updated"
            ui_data = {
                "conversation_id": str(event.conversation_id),
                "from_phone": event.metadata.get("from_phone", "Unknown")
            }
        elif event.event_name == "intent_classified":
            ui_event = "intent_extracted"
            ui_data = {
                "conversation_id": str(event.conversation_id),
                "intent": event.metadata.get("intent", "Unknown"),
                "confidence": event.metadata.get("confidence", 0.0)
            }
        elif event.event_name == "customer_updated":
            ui_event = "customer_updated"
            ui_data = {
                "customer_id": str(event.customer_id),
                "customer_name": event.metadata.get("name", "Unknown")
            }
        elif event.event_name == "lead_stage_updated":
            ui_event = "lead_stage_changed"
            ui_data = {
                "customer_id": str(event.customer_id),
                "new_stage": event.metadata.get("stage", "Unknown")
            }
        elif event.event_name == "memory_summarized":
            ui_event = "memory_updated"
            ui_data = {
                "customer_id": str(event.customer_id)
            }
        else:
            # Fallback for other events
            ui_event = "system_notification"
            ui_data = {
                "type": event.event_name,
                "customer_id": str(event.customer_id) if event.customer_id else None
            }

        logger.debug(f"UIEventConsumer broadcasting {ui_event} to workspace {event.workspace_id}")
        await ws_manager.broadcast_to_workspace(
            workspace_id=event.workspace_id,
            payload={
                "event": ui_event,
                "data": ui_data
            }
        )
