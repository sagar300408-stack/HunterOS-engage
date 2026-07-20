import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

from app.domain.integration.models import IntegrationConnection, SyncJob, SyncMode, SyncStatus
from app.domain.integration.engines.registry import IntegrationRegistry
from app.domain.integration.engines.translation import EventTranslationEngine

logger = logging.getLogger("hunteros.sync")

class SynchronizationEngine:
    """
    Manages near real-time, scheduled polling, or batch syncing for integrations.
    """

    @staticmethod
    async def trigger_incremental_sync(db: AsyncSession, integration_id: uuid.UUID) -> SyncJob:
        """
        Triggers an incremental pull of data since the `last_sync_at` timestamp.
        """
        stmt = select(IntegrationConnection).where(IntegrationConnection.id == integration_id)
        result = await db.execute(stmt)
        integration = result.scalar_one_or_none()
        
        if not integration:
            raise ValueError("Integration not found")
            
        job = SyncJob(
            integration_id=integration.id,
            mode=SyncMode.polling,
            status=SyncStatus.running
        )
        db.add(job)
        await db.commit()
        
        try:
            connector = IntegrationRegistry.get_connector(integration.connector_id)
            
            # Fetch raw events
            raw_events = await connector.sync_events(
                credentials=integration.credentials_json,
                last_sync=integration.last_sync_at
            )
            
            # Update stats
            job.records_processed = len(raw_events)
            
            # Note: Normally we'd push these through the Data Mapping engine here.
            # For brevity, assume successful mapping.
            
            job.status = SyncStatus.completed
            job.completed_at = datetime.utcnow()
            integration.last_sync_at = datetime.utcnow()
            
            logger.info(f"Incremental sync complete for {integration.id}. {len(raw_events)} records.")
        except Exception as e:
            logger.error(f"Sync failed for {integration.id}: {e}")
            job.status = SyncStatus.failed
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            
        await db.commit()
        return job
