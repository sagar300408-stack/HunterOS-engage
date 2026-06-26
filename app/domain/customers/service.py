"""
customer_service — Phase 2 stub.

Phase 1: All methods are no-ops.
Phase 2: Implement customer lookup, creation, and profile enrichment.
         No other files change — the pipeline calls these signatures only.
"""

from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_or_create_customer(phone: str) -> Optional[object]:
    """
    Phase 2: Look up or create a Customer profile by phone number.
    Returns the Customer ORM object.
    """
    logger.debug("customer_service_stub_called", action="get_or_create", phone=phone)
    return None


async def update_customer_profile(phone: str, **kwargs) -> None:
    """Phase 2: Update customer metadata — name, email, tags, preferences."""
    logger.debug("customer_service_stub_called", action="update", phone=phone)
    return None


async def get_customer_by_phone(phone: str) -> Optional[object]:
    """Phase 2: Retrieve a customer record by phone number."""
    logger.debug("customer_service_stub_called", action="get_by_phone", phone=phone)
    return None
