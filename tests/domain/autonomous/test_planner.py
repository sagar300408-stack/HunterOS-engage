import uuid
import pytest

from app.domain.autonomous.planner import PlannerRegistry
from app.domain.autonomous.models import OperationalOpportunity

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


def test_reengagement_planner():
    registry = PlannerRegistry()
    planner = registry.get_planner("REENGAGE_CUSTOMER")
    
    workspace_id = uuid.uuid4()
    opp_id = uuid.uuid4()
    
    opp = OperationalOpportunity(
        id=opp_id,
        workspace_id=workspace_id,
        source="RECOMMENDATION",
        source_reference_id="cust_123",
        opportunity_type="REENGAGE_CUSTOMER",
        priority="HIGH"
    )
    
    plan, steps = planner.generate_plan(opp)
    
    assert plan.workspace_id == workspace_id
    assert plan.opportunity_id == opp_id
    assert plan.mission_priority == 1
    assert plan.failure_strategy == "COMPENSATE"
    
    assert len(steps) == 3
    assert steps[0].type == "ACTION"
    assert steps[0].inputs["target_id"] == "cust_123"
    
    assert steps[1].type == "WAIT"
    assert steps[1].dependencies == [0]
    
    assert steps[2].type == "VALIDATION"
    assert steps[2].dependencies == [1]


def test_planner_registry_not_found():
    registry = PlannerRegistry()
    
    with pytest.raises(ValueError):
        registry.get_planner("NON_EXISTENT_TYPE")
