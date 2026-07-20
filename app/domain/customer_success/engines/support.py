import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.customer_success.models import SupportTicket, SupportTicketStatus

logger = logging.getLogger("hunteros.cs")

class SupportEngine:
    """
    Manages Enterprise Support Ticketing and SLA compliance.
    """

    @staticmethod
    async def open_ticket(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, subject: str, description: str) -> SupportTicket:
        ticket = SupportTicket(
            workspace_id=workspace_id,
            user_id=user_id,
            subject=subject,
            description=description
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        logger.info(f"Opened Support Ticket {ticket.id} for Workspace {workspace_id}")
        return ticket
