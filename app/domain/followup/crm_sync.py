from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

async def sync_followup_created(session: AsyncSession, followup_id: UUID, customer_id: UUID, reason: str, workspace_id: UUID):
    # Stub: Sync to external CRM (Hubspot/Salesforce)
    pass

async def sync_followup_sent(session: AsyncSession, followup_id: UUID, customer_id: UUID, channel: str, provider_id: str, workspace_id: UUID):
    # Stub: Sync to external CRM
    pass

async def sync_followup_cancelled(session: AsyncSession, followup_id: UUID, reason: str, workspace_id: UUID):
    # Stub: Sync to external CRM
    pass
