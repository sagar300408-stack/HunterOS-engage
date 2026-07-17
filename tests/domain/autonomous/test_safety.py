import pytest

from app.domain.autonomous.safety import SafetyEnforcer
from app.domain.autonomous.models import PlanStep

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


def test_safety_enforcer_workspace_inactive():
    step = PlanStep(inputs={}, retry_policy={})
    settings = {"is_active": False}
    
    is_safe, reason = SafetyEnforcer.evaluate_dispatch(step, settings)
    assert not is_safe
    assert "inactive" in reason


def test_safety_enforcer_maintenance():
    step = PlanStep(inputs={}, retry_policy={})
    settings = {"is_active": True, "maintenance_mode": True}
    
    is_safe, reason = SafetyEnforcer.evaluate_dispatch(step, settings)
    assert not is_safe
    assert "maintenance" in reason


def test_safety_enforcer_quotas():
    step = PlanStep(inputs={}, retry_policy={})
    settings = {
        "is_active": True, 
        "current_monthly_executions": 1000, 
        "max_monthly_executions": 1000
    }
    
    is_safe, reason = SafetyEnforcer.evaluate_dispatch(step, settings)
    assert not is_safe
    assert "quota" in reason


def test_safety_enforcer_concurrency():
    step = PlanStep(inputs={}, retry_policy={})
    settings = {
        "is_active": True, 
        "current_concurrent_plans": 10, 
        "max_concurrent_plans": 10
    }
    
    is_safe, reason = SafetyEnforcer.evaluate_dispatch(step, settings)
    assert not is_safe
    assert "Concurrency limit" in reason


def test_safety_enforcer_retry_budget():
    step = PlanStep(
        inputs={"_attempts": 3},
        retry_policy={"max_retries": 3}
    )
    settings = {"is_active": True}
    
    is_safe, reason = SafetyEnforcer.evaluate_dispatch(step, settings)
    assert not is_safe
    assert "Retry budget" in reason


def test_safety_enforcer_pass():
    step = PlanStep(
        inputs={"_attempts": 0},
        retry_policy={"max_retries": 3}
    )
    settings = {
        "is_active": True, 
        "current_concurrent_plans": 2, 
        "max_concurrent_plans": 10,
        "current_monthly_executions": 50, 
        "max_monthly_executions": 1000
    }
    
    is_safe, reason = SafetyEnforcer.evaluate_dispatch(step, settings)
    assert is_safe
    assert "passed" in reason
