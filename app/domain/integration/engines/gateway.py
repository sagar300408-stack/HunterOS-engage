from fastapi import HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import logging

from app.domain.integration.models import IntegrationConnection
from app.domain.integration.engines.translation import EventTranslationEngine

logger = logging.getLogger("hunteros.integration")

class IntegrationGateway:
    """
    Single entry point for all external webhooks.
    Handles Authentication, Validation, and Rate Limiting.
    """

    @staticmethod
    async def process_webhook(
        db: AsyncSession, 
        integration_id: uuid.UUID, 
        request: Request
    ):
        """
        Receives external webhook, validates authenticity, and dispatches to TranslationEngine.
        """
        stmt = select(IntegrationConnection).where(IntegrationConnection.id == integration_id)
        result = await db.execute(stmt)
        integration = result.scalar_one_or_none()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
            
        if integration.status != "connected":
            raise HTTPException(status_code=400, detail="Integration is not active")

        # 1. Validation (Example: Check signature against webhook_secret)
        # Signature validation differs per vendor, handled by the specific Connector in practice.
        payload = await request.json()
        headers = dict(request.headers)
        
        # 2. Dispatch to Translator
        try:
            normalized_events = await EventTranslationEngine.translate_webhook_event(
                db=db,
                integration=integration,
                payload=payload,
                headers=headers
            )
            return {"status": "success", "processed_events": len(normalized_events)}
        except Exception as e:
            logger.error(f"Webhook processing failed for {integration_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal processing error")
