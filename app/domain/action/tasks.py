import asyncio
from uuid import UUID
from app.celery_app import celery_app
from app.integrations.postgres.database import get_session
from app.events.bus.event_bus import EventBus
from app.domain.integration.engine import IntegrationEngine
from app.domain.integration.credentials import JsonCredentialProvider
from app.domain.action.engine import ActionEngine

@celery_app.task(bind=True, name="app.domain.action.tasks.execute_action_task", max_retries=3)
def execute_action_task(self, action_id_str: str):
    action_id = UUID(action_id_str)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    async def _run():
        async with get_session() as session:
            event_bus = EventBus(session)
            cred_provider = JsonCredentialProvider()
            integration_engine = IntegrationEngine(session, cred_provider, event_bus)
            engine = ActionEngine(session, event_bus, integration_engine)
            
            await engine._execute(action_id, celery_task=self)
            
    loop.run_until_complete(_run())
