import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.security.models import DEFAULT_WORKSPACE_ID
from app.domain.customers.models import Customer
from app.domain.conversations.models import Conversation
from app.domain.impact.models import ImpactEvent, ValueAttribution, ImpactCategory, BusinessTargets
from app.domain.intent.models import PromptConfig
from app.domain.kpi.engine import KpiIntelligenceEngine
from app.domain.briefing.engine import ExecutiveBriefingEngine
from app.domain.briefing.bootstrap import bootstrap_briefings
from app.domain.ui.engines.composer import ComposerEngine
from app.domain.ui.repository import UIRepository
from tests.domain.events.conftest import pg_session_factory, pg_engine, pg_session

@pytest.mark.asyncio
async def test_cross_wave_e2e_roi_briefing_intent(pg_session_factory, pg_engine):
    # Ensure tables exist
    async with pg_engine.begin() as conn:
        from app.domain.intent.models import Base as IntentBase
        from app.domain.kpi.models import Base as KPIBase
        await conn.run_sync(IntentBase.metadata.create_all)
        await conn.run_sync(KPIBase.metadata.create_all)
        
    bootstrap_briefings()

    workspace_id = uuid4()

    async with pg_session_factory() as session:
        async with session.begin():
            # 2. Add PromptConfig (O10)
            prompt_config = PromptConfig(workspace_id=workspace_id, prompt_text="E2E Prompt")
            session.add(prompt_config)

            # 3. Add BusinessTargets (O11)
            targets = BusinessTargets(
                workspace_id=workspace_id,
                kpi_name="target_deals_closed",
                target_value=10.0,
            )
            session.add(targets)
            
            # 4. Add Customer & Conversation
            import random
            phone = f"+155500{random.randint(10000, 99999)}"
            customer = Customer(id=uuid4(), workspace_id=workspace_id, name="Test Cust", phone=phone)
            session.add(customer)
            await session.flush()
            conversation = Conversation(id=uuid4(), customer_id=customer.id, workspace_id=workspace_id, customer_phone=customer.phone)
            session.add(conversation)
            
            # 5. Add ImpactEvents (O14)
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
                estimated_financial_value=30.0,
                confidence_score=0.9
            )
            attr2 = ValueAttribution(
                event_id=event.id,
                workspace_id=workspace_id,
                category=ImpactCategory.REVENUE_PROTECTION,
                estimated_financial_value=500.0,
                confidence_score=0.8
            )
            session.add_all([attr1, attr2])

    async with pg_session_factory() as session:
        # 6. Test KPI Override (O11)
        kpi_engine = KpiIntelligenceEngine(session)
        kpis = await kpi_engine.refresh_kpis(workspace_id, "workspace", workspace_id)
        assert kpis is not None

        # 7. Test Briefing generation (O12)
        briefing_engine = ExecutiveBriefingEngine(session)
        briefing = await briefing_engine.generate_briefing(workspace_id, "ceo_daily")
        assert briefing is not None
        assert isinstance(briefing.executive_summary, str)
        assert len(briefing.executive_summary) > 0

        # 8. Test ROI UI (O14)
        repo = UIRepository(session)
        layout = await ComposerEngine.compose_dashboard(repo, workspace_id, role="executive")
        assert layout is not None
        
        # Find ROI widget
        roi_widget = next((w for w in layout.widgets if w.widget_key == "roi_summary"), None)
        assert roi_widget is not None
        # Payload should have real data
        assert roi_widget.data_payload["roi_value"] == 530.0
