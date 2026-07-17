import uuid
import pytest
from unittest.mock import AsyncMock

from app.domain.autonomous.coordinator import MissionCoordinator
from app.domain.autonomous.models import ExecutionPlan, PlanStep, PlanStatus, StepStatus

# SQLAlchemy mapping requirements
from app.domain.action import models as action_models
from app.domain.integration import models as integration_models
from app.domain.briefing import models as briefing_models
from app.domain.recommendation import models as rec_models
from app.domain.insight import models as insight_models
from app.domain.health import models as health_models
from app.domain.kpi import models as kpi_models
from app.domain.conversations import models as conv_models
from app.domain.customers import models as cust_models
from app.domain.scheduling import models as sched_models
from app.domain.followup import models as followup_models
from app.domain.intent import models as intent_models
from app.domain.memory import models as memory_models
from app.domain.approval import models as approval_models
from app.domain.marketplace import models as marketplace_models
from app.domain.autonomous import models as autonomous_models


@pytest.mark.asyncio
async def test_reconcile_plan_starts_executing():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    
    coordinator = MissionCoordinator(mock_session, mock_event_bus)
    
    plan_id = uuid.uuid4()
    plan = ExecutionPlan(id=plan_id, status=PlanStatus.PLANNED.value)
    
    # 2 steps
    step1 = PlanStep(id=uuid.uuid4(), plan_id=plan_id, step_index=0, type="ACTION", status=StepStatus.PENDING.value, inputs={}, retry_policy={})
    step2 = PlanStep(id=uuid.uuid4(), plan_id=plan_id, step_index=1, type="WAIT", status=StepStatus.PENDING.value, dependencies=[0], inputs={}, retry_policy={})
    
    coordinator.repo.get_plan = AsyncMock(return_value=plan)
    coordinator.repo.get_steps_for_plan = AsyncMock(return_value=[step1, step2])
    
    async def mock_save_plan(p):
        return p
    coordinator.repo.save_plan = AsyncMock(side_effect=mock_save_plan)
    
    async def mock_save_step(s):
        return s
    coordinator.repo.save_step = AsyncMock(side_effect=mock_save_step)
    
    coordinator._record_journal = AsyncMock()
    coordinator._publish_event = AsyncMock()
    
    # Run reconciliation
    plan = await coordinator.reconcile_plan(plan_id, triggering_event="test_trigger")
    
    # Plan should be EXECUTING
    assert plan.status == PlanStatus.EXECUTING.value
    
    # Step 1 should be dispatched (EXECUTING)
    assert step1.status == StepStatus.EXECUTING.value
    
    # Step 2 should still be pending
    assert step2.status == StepStatus.PENDING.value
    
    # Check journal and events
    assert coordinator._record_journal.call_count >= 2
    assert coordinator._publish_event.call_count >= 2


@pytest.mark.asyncio
async def test_reconcile_plan_completes():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    
    coordinator = MissionCoordinator(mock_session, mock_event_bus)
    
    plan_id = uuid.uuid4()
    plan = ExecutionPlan(id=plan_id, status=PlanStatus.EXECUTING.value)
    
    # Both steps SUCCESS
    step1 = PlanStep(id=uuid.uuid4(), plan_id=plan_id, step_index=0, type="ACTION", status=StepStatus.SUCCESS.value)
    step2 = PlanStep(id=uuid.uuid4(), plan_id=plan_id, step_index=1, type="WAIT", status=StepStatus.SUCCESS.value)
    
    coordinator.repo.get_plan = AsyncMock(return_value=plan)
    coordinator.repo.get_steps_for_plan = AsyncMock(return_value=[step1, step2])
    
    async def mock_save_plan(p):
        return p
    coordinator.repo.save_plan = AsyncMock(side_effect=mock_save_plan)
    
    coordinator._record_journal = AsyncMock()
    coordinator._publish_event = AsyncMock()
    
    plan = await coordinator.reconcile_plan(plan_id)
    
    assert plan.status == PlanStatus.COMPLETED.value
    coordinator._record_journal.assert_called()
    coordinator._publish_event.assert_called()


@pytest.mark.asyncio
async def test_reconcile_plan_fails():
    mock_session = AsyncMock()
    mock_event_bus = AsyncMock()
    
    coordinator = MissionCoordinator(mock_session, mock_event_bus)
    
    plan_id = uuid.uuid4()
    plan = ExecutionPlan(id=plan_id, status=PlanStatus.EXECUTING.value)
    
    step1 = PlanStep(id=uuid.uuid4(), plan_id=plan_id, step_index=0, type="ACTION", status=StepStatus.FAILED.value)
    step2 = PlanStep(id=uuid.uuid4(), plan_id=plan_id, step_index=1, type="WAIT", status=StepStatus.PENDING.value)
    
    coordinator.repo.get_plan = AsyncMock(return_value=plan)
    coordinator.repo.get_steps_for_plan = AsyncMock(return_value=[step1, step2])
    
    async def mock_save_plan(p):
        return p
    coordinator.repo.save_plan = AsyncMock(side_effect=mock_save_plan)
    
    coordinator._record_journal = AsyncMock()
    coordinator._publish_event = AsyncMock()
    
    plan = await coordinator.reconcile_plan(plan_id)
    
    assert plan.status == PlanStatus.FAILED.value
