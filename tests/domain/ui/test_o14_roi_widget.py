import pytest
import uuid
from datetime import datetime, timezone, timedelta

from app.domain.ui.engines.composer import ComposerEngine
from app.domain.ui.repository import UIRepository
from app.domain.impact.models import ValueAttribution, ImpactCategory, ImpactEvent
from app.domain.customers.models import Customer
from app.domain.conversations.models import Conversation
from tests.domain.events.conftest import pg_session_factory, pg_engine, pg_session

@pytest.mark.asyncio
async def test_o14_real_roi_widget_integration(pg_session_factory):
    # We will use the pg_session_factory to ensure we test real DB persistence
    workspace_id = uuid.uuid4()
    
    async with pg_session_factory() as session:
        async with session.begin():
            # Create some impact events and value attributions
            event = ImpactEvent(
                workspace_id=workspace_id,
                event_type="test_event",
                source_feature="test_feature"
            )
            session.add(event)
            await session.flush()
            
            attr1 = ValueAttribution(
                event_id=event.id,
                workspace_id=workspace_id,
                category=ImpactCategory.TIME_SAVINGS,
                estimated_financial_value=1250.00,
                confidence_score=0.9
            )
            attr2 = ValueAttribution(
                event_id=event.id,
                workspace_id=workspace_id,
                category=ImpactCategory.OPPORTUNITY_RECOVERY,
                estimated_financial_value=5000.00,
                confidence_score=0.8
            )
            session.add(attr1)
            session.add(attr2)
            
    # Now run the UI composer as the API would
    async with pg_session_factory() as session:
        repo = UIRepository(session)
        payload = await ComposerEngine.compose_dashboard(repo, workspace_id, role="executive")
        
        # In executive dashboard, we expect the "roi_summary" widget to be present
        roi_widget = next((w for w in payload.widgets if w.widget_key == "roi_summary"), None)
        assert roi_widget is not None, "roi_summary widget must be present"
        
        # Verify the calculation is deterministic and real (1250 + 5000 = 6250)
        assert roi_widget.data_payload["roi_value"] == 6250.00
        assert roi_widget.data_payload["currency"] == "USD"
        
        # Verify there is no fake 1.5M fallback
        assert roi_widget.data_payload["roi_value"] != 1500000.00
