"""
customer_service — Customer identification and profile management.

Public API (stable — no later phase queries the DB directly):
    get_customer(session, phone) -> Customer | None
    get_or_create_customer(session, phone, name) -> Customer
    update_customer_profile(session, customer_id, **kwargs) -> Customer
    update_last_interaction(session, customer_id) -> None

Design:
    - Phone number is the natural key. One row per customer, ever.
    - get_or_create_customer is idempotent — safe to call on every message.
    - All methods accept AsyncSession — no global state.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.customers.models import Customer, CustomerStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_customer(
    session: AsyncSession,
    phone: str,
) -> Optional[Customer]:
    """
    Retrieve a customer record by phone number.
    Returns None if the customer does not exist yet.
    """
    result = await session.execute(
        select(Customer).where(Customer.phone == phone)
    )
    return result.scalar_one_or_none()


async def get_or_create_customer(
    session: AsyncSession,
    phone: str,
    name: Optional[str] = None,
) -> Customer:
    """
    Look up or create a Customer profile by phone number.

    Idempotent — calling this multiple times for the same phone
    always returns the same Customer row. Never creates duplicates.

    Args:
        session: Active async database session.
        phone:   Customer's WhatsApp phone number (the natural key).
        name:    Contact name from the WhatsApp message (optional).

    Returns:
        The existing or newly created Customer ORM object.
    """
    customer = await get_customer(session, phone)

    if customer:
        # Update name if we now have one and didn't before
        if name and not customer.name:
            customer.name = name
            await session.flush()
            logger.info(
                "customer_name_updated",
                customer_id=str(customer.id),
                phone=phone,
                name=name,
            )
        else:
            logger.debug(
                "customer_found",
                customer_id=str(customer.id),
                phone=phone,
            )
        return customer

    # ── New customer ──────────────────────────────────────────────────────────
    customer = Customer(
        phone=phone,
        name=name,
        status=CustomerStatus.new,
    )
    session.add(customer)
    await session.flush()  # get UUID before commit

    logger.info(
        "customer_created",
        customer_id=str(customer.id),
        phone=phone,
        name=name,
    )

    return customer


async def update_customer_profile(
    session: AsyncSession,
    customer_id: UUID,
    **kwargs,
) -> Optional[Customer]:
    """
    Update customer metadata — name, email, notes, status, preferred_language.

    Only fields explicitly passed in kwargs are updated.
    Unrecognised keys are ignored to prevent accidental overwrites.

    Allowed fields: name, email, status, preferred_language, notes
    """
    allowed_fields = {"name", "email", "status", "preferred_language", "notes"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

    if not updates:
        return None

    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        logger.warning("customer_not_found_for_update", customer_id=str(customer_id))
        return None

    for field, value in updates.items():
        setattr(customer, field, value)

    await session.flush()

    logger.info(
        "customer_profile_updated",
        customer_id=str(customer_id),
        updated_fields=list(updates.keys()),
    )

    return customer


async def update_last_interaction(
    session: AsyncSession,
    customer_id: UUID,
) -> None:
    """
    Stamp last_interaction with the current UTC time.

    Called after every AI response is successfully sent.
    Used by future dashboard analytics and follow-up scheduling.
    """
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if customer:
        customer.last_interaction = datetime.now(timezone.utc)
        await session.flush()
        logger.debug(
            "customer_last_interaction_updated",
            customer_id=str(customer_id),
        )
