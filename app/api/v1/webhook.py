"""
Versioned webhook route — /api/v1/webhook

This is a thin route layer. No business logic lives here.
All processing is delegated to the pipeline stages.

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
from app.pipeline.ai import process_with_ai
from app.pipeline.followup import schedule_followup
from app.pipeline.receive import receive
from app.pipeline.respond import send_response
from app.utils.logger import get_logger
from app.utils.context import is_demo_context
from app.services.communication import process_whatsapp_pipeline

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
    description="Processes incoming WhatsApp messages through the full pipeline.",
)
async def receive_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    POST /api/v1/webhook — receive and process incoming WhatsApp messages.

    Pipeline (Phase 3):
        receive → process_with_ai (memory + intent + AI) → send_response → schedule_followup
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

        # ── Stage 1 + 2: Receive + Customer Identification ────────────────────
        result = await receive(payload, session)

        if result is None:
            return {"status": "ok", "processed": False}

        # Phase 3: unpack 4-tuple (conversation, message_data, customer, message)
        conversation, message_data, customer, message = result

        # ── Stage 4: AI Processing (memory + intent + conversational AI) ──────
        ai_result = await process_with_ai(
            conversation_id=conversation.id,
            message_id=message.id,
            customer=customer,
            user_content=message_data["content"],
            session=session,
        )

        # ── Stage 6: Respond ──────────────────────────────────────────────────
        import time
        t0 = time.monotonic()
        await send_response(
            to_phone=message_data["from_phone"],
            conversation_id=conversation.id,
            ai_result=ai_result,
            session=session,
        )
        t_respond = int((time.monotonic() - t0) * 1000)

        # Log Stage 7: reply_sent (Phase 4)
        try:
            from app.domain.dashboard.service import log_pipeline_step
            await log_pipeline_step(
                session=session,
                message_id=message.id,
                step="reply_sent",
                duration_ms=t_respond,
                payload={"reply": ai_result["content"], "to": message_data["from_phone"]},
                workspace_id=customer.workspace_id,
            )
        except Exception as e:
            logger.error("failed_to_log_reply_sent_step", error=str(e))

        # Broadcast live update to WebSocket clients (Phase 4)
        try:
            from app.integrations.websocket.manager import ws_manager
            await ws_manager.broadcast({
                "event": "conversation_updated",
                "data": {
                    "conversation_id": str(conversation.id),
                    "from_phone": message_data["from_phone"],
                }
            })
        except Exception as e:
            logger.error("failed_to_broadcast_websocket_event", error=str(e))

        # ── Stage 5: Follow-up (stub — Phase 6) ──────────────────────────────
        await schedule_followup(
            conversation_id=str(conversation.id),
            from_phone=message_data["from_phone"],
            ai_response=ai_result["content"],
        )

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
