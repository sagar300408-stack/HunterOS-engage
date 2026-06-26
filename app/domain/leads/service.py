"""
lead_service — Phase 3 stub.

Phase 1: All methods are no-ops.
Phase 3: Implement lead scoring, qualification, CRM sync, and pipeline management.
         No other files change — the pipeline calls these signatures only.
"""

from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def qualify_lead(phone: str, conversation_id: str) -> Optional[dict]:
    """
    Phase 3: Score and qualify a lead based on conversation content.
    Returns a qualification dict: {score, intent, urgency, ...}
    """
    logger.debug("lead_service_stub_called", action="qualify", phone=phone)
    return None


async def create_lead(phone: str, source: str = "whatsapp") -> None:
    """Phase 3: Create a lead record and optionally sync to CRM."""
    logger.debug("lead_service_stub_called", action="create", phone=phone, source=source)
    return None


async def update_lead_stage(lead_id: str, stage: str) -> None:
    """Phase 3: Move a lead through the pipeline stages."""
    logger.debug("lead_service_stub_called", action="update_stage", lead_id=lead_id, stage=stage)
    return None
