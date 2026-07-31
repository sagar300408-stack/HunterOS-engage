"""
Versioned webhook route — /api/v1/webhook

This is a pure controller as per HunterOS Phase 7 Architecture.
It ONLY maps the HTTP request to a RawWebhookEvent, publishes it to the EventBus,
and returns 200 immediately. No orchestration lives here.

Why 200 always on POST?
  Meta marks your webhook as failed if it receives anything other than 200.
  Application-level errors are caught, logged, and return 200 to prevent
  Meta from disabling your webhook and flooding with retries.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.meta.webhook import verify_hub_challenge
from app.integrations.postgres.database import get_db
from app.utils.logger import get_logger
from app.utils.context import is_demo_context
from app.events.message_events import RawWebhookEvent

router = APIRouter(prefix="/api/v1", tags=["Webhook v1"])
logger = get_logger(__name__)


@router.get(
    "/webhook",
    summary="Meta Webhook Verification",
    description="Handles the Meta hub.challenge verification handshake.",
)
async def verify_webhook(
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    """GET /api/v1/webhook — Meta webhook verification handshake."""
    challenge = verify_hub_challenge(hub_mode, hub_verify_token, hub_challenge)

    if challenge is None:
        raise HTTPException(status_code=403, detail="Webhook verification failed.")

    return Response(content=challenge, media_type="text/plain")


@router.post(
    "/webhook",
    summary="Receive WhatsApp Message",
    description="Publishes incoming WhatsApp messages to the EventBus.",
)
async def receive_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    print("🔥 POST webhook reached")
    """
    POST /api/v1/webhook — receive incoming WhatsApp messages.
    
    Phase 7 Architecture: This is a pure controller. 
    It publishes a RawWebhookEvent and returns 200 immediately.
    """
    try:
        payload = await request.json()
        if payload.get("is_demo"):
            is_demo_context.set(True)

        logger.debug(
            "webhook_payload_received",
            object_type=payload.get("object"),
        )

        # Only process WhatsApp Business Account webhooks
        if payload.get("object") != "whatsapp_business_account":
            logger.debug(
                "webhook_ignored",
                reason="not_whatsapp_business_account",
                object_type=payload.get("object"),
            )
            return {"status": "ignored", "reason": "not_whatsapp_business_account"}

        # Create the event
        event = RawWebhookEvent(payload=payload)
        
        # Publish to the EventBus (which persists it synchronously in the DB transaction and queues a Celery task)
        event_bus = request.app.state.event_bus
        await event_bus.publish(session, event)
        
        # Commit the transaction so the event is persisted (Celery task will pick it up)
        await session.commit()

        return {"status": "ok", "processed": True}

    except Exception as exc:
        logger.error(
            "webhook_processing_error",
            error=str(exc),
            error_type=type(exc).__name__,
            exc_info=True,
        )
        # Always return 200 — prevents Meta from disabling the webhook
        return {"status": "error", "detail": "Internal processing error"}
