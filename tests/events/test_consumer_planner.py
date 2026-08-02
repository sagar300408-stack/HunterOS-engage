"""
Tests for Phase 1.4 - Milestone 2: Consumer Dependency Graph & Execution Planning
"""

import asyncio
import uuid
import pytest
from typing import List, Type

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory
from app.events.model.actor_types import ActorType
from app.events.worker.planner import (
    PlanBuilder,
    ExecutionPlan,
    ExecutionStage,
    PlanValidationFailed,
)
from app.events.worker.orchestrator import (
    ConsumerOrchestrator,
    ConsumerResult,
    ConsumerStatus,
    ExecutionReport,
)
from app.events.registry.registry import ConsumerRegistry
from app.events.bootstrap.register_consumers import validate_and_log_startup_plans


class DummyEvent(UniversalBaseEvent):
    class Config:
        extra = "allow"


def make_dummy_event() -> DummyEvent:
    return DummyEvent(
        workspace_id=uuid.uuid4(),
        actor_type=ActorType.CUSTOMER,
        source_subsystem="test",
        category=EventCategory.CONVERSATION,
        event_name="DummyEvent",
    )


# ── Consumer Fixtures ────────────────────────────────────────────────────────

class ConsumerA(EventConsumer):
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [DummyEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        pass


class ConsumerB(EventConsumer):
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [DummyEvent]

    def depends_on(self) -> List[Type[EventConsumer]]:
        return [ConsumerA]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        pass


class ConsumerC(EventConsumer):
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [DummyEvent]

    def depends_on(self) -> List[Type[EventConsumer]]:
        return [ConsumerB]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        pass


class ConsumerD(EventConsumer):
    """Independent consumer (runs in Stage 0 alongside ConsumerA)."""
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [DummyEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        pass


# ── Tests: Topological Sorting & Multi-Stage DAG ─────────────────────────────

def test_linear_dependency_stages():
    """A -> B -> C should result in 3 stages: [A], [B], [C]."""
    consumers = [ConsumerC(), ConsumerB(), ConsumerA()]
    plan = PlanBuilder.build("DummyEvent", consumers)

    assert plan.stage_count == 3
    assert plan.consumer_count == 3

    stage0_names = [c.__class__.__name__ for c in plan.stages[0].consumers]
    stage1_names = [c.__class__.__name__ for c in plan.stages[1].consumers]
    stage2_names = [c.__class__.__name__ for c in plan.stages[2].consumers]

    assert stage0_names == ["ConsumerA"]
    assert stage1_names == ["ConsumerB"]
    assert stage2_names == ["ConsumerC"]


def test_branching_and_diamond_dag():
    """
    Diamond graph:
        A
       / \
      B   D
       \ /
        C
    Stage 0: [A]
    Stage 1: [B, D] (concurrent/independent)
    Stage 2: [C] (waits for both B and D)
    """
    class DiamondA(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        async def handle_event(self, e): pass

    class DiamondB(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [DiamondA]
        async def handle_event(self, e): pass

    class DiamondD(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [DiamondA]
        async def handle_event(self, e): pass

    class DiamondC(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [DiamondB, DiamondD]
        async def handle_event(self, e): pass

    consumers = [DiamondC(), DiamondD(), DiamondA(), DiamondB()]
    plan = PlanBuilder.build("DummyEvent", consumers)

    assert plan.stage_count == 3
    assert [c.__class__.__name__ for c in plan.stages[0].consumers] == ["DiamondA"]
    assert set(c.__class__.__name__ for c in plan.stages[1].consumers) == {"DiamondB", "DiamondD"}
    assert [c.__class__.__name__ for c in plan.stages[2].consumers] == ["DiamondC"]


# ── Tests: Cycle Detection ───────────────────────────────────────────────────

def test_direct_cycle_detection():
    """A -> B -> A should raise PlanValidationFailed with CIRCULAR_DEPENDENCY."""
    class CycleA(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [CycleB]
        async def handle_event(self, e): pass

    class CycleB(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [CycleA]
        async def handle_event(self, e): pass

    with pytest.raises(PlanValidationFailed) as exc_info:
        PlanBuilder.build("DummyEvent", [CycleA(), CycleB()])

    assert any(err.code == "CIRCULAR_DEPENDENCY" for err in exc_info.value.errors)
    assert set(exc_info.value.errors[0].consumers) == {"CycleA", "CycleB"}


def test_indirect_cycle_detection():
    """A -> B -> C -> A should raise PlanValidationFailed with CIRCULAR_DEPENDENCY."""
    class IndCycleA(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [IndCycleC]
        async def handle_event(self, e): pass

    class IndCycleB(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [IndCycleA]
        async def handle_event(self, e): pass

    class IndCycleC(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [IndCycleB]
        async def handle_event(self, e): pass

    with pytest.raises(PlanValidationFailed) as exc_info:
        PlanBuilder.build("DummyEvent", [IndCycleA(), IndCycleB(), IndCycleC()])

    assert any(err.code == "CIRCULAR_DEPENDENCY" for err in exc_info.value.errors)
    assert set(exc_info.value.errors[0].consumers) == {"IndCycleA", "IndCycleB", "IndCycleC"}


# ── Tests: Missing Dependencies & Duplicates ────────────────────────────────

def test_missing_dependency_detection():
    """Consumer declaring depends_on with an unregistered consumer class."""
    class UnregisteredConsumer(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        async def handle_event(self, e): pass

    class DepMissingConsumer(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [UnregisteredConsumer]
        async def handle_event(self, e): pass

    with pytest.raises(PlanValidationFailed) as exc_info:
        PlanBuilder.build("DummyEvent", [DepMissingConsumer()])

    assert any(err.code == "MISSING_DEPENDENCY" for err in exc_info.value.errors)


def test_duplicate_consumer_detection():
    """Two instances of the same consumer class for the same event."""
    with pytest.raises(PlanValidationFailed) as exc_info:
        PlanBuilder.build("DummyEvent", [ConsumerA(), ConsumerA()])

    assert any(err.code == "DUPLICATE_CONSUMER" for err in exc_info.value.errors)


def test_invalid_policy_combination():
    """CRITICAL/ORDERED consumer depending on a BACKGROUND consumer."""
    class BgConsumer(EventConsumer):
        def get_execution_policy(self): return ExecutionPolicy.BACKGROUND
        def get_subscriptions(self): return [DummyEvent]
        async def handle_event(self, e): pass

    class BadOrderedConsumer(EventConsumer):
        def get_execution_policy(self): return ExecutionPolicy.ORDERED
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [BgConsumer]
        async def handle_event(self, e): pass

    with pytest.raises(PlanValidationFailed) as exc_info:
        PlanBuilder.build("DummyEvent", [BgConsumer(), BadOrderedConsumer()])

    assert any(err.code == "INVALID_POLICY_COMBO" for err in exc_info.value.errors)


# ── Tests: Execution & Failure Isolation with Stages ─────────────────────────

@pytest.mark.asyncio
async def test_run_plan_stage_execution_order():
    """Verify execution order matches stage order strictly."""
    execution_order = []

    class Stage0(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        async def handle_event(self, e):
            execution_order.append("Stage0")

    class Stage1(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [Stage0]
        async def handle_event(self, e):
            execution_order.append("Stage1")

    class Stage2(EventConsumer):
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [Stage1]
        async def handle_event(self, e):
            execution_order.append("Stage2")

    plan = PlanBuilder.build("DummyEvent", [Stage2(), Stage0(), Stage1()])
    event = make_dummy_event()
    report = await ConsumerOrchestrator.run_plan(event, plan, uuid.uuid4())

    assert not report.has_errors
    assert execution_order == ["Stage0", "Stage1", "Stage2"]
    assert len(report.results) == 3
    assert report.results[0].stage_index == 0
    assert report.results[1].stage_index == 1
    assert report.results[2].stage_index == 2


@pytest.mark.asyncio
async def test_critical_failure_halts_downstream_stages():
    """
    Stage 0 (CRITICAL) fails -> Stage 1 consumers must be SKIPPED.
    """
    class CritStage0(EventConsumer):
        def get_execution_policy(self): return ExecutionPolicy.CRITICAL
        def get_subscriptions(self): return [DummyEvent]
        async def handle_event(self, e):
            raise RuntimeError("stage 0 critical crash")

    class DownstreamStage1(EventConsumer):
        ran = False
        def get_subscriptions(self): return [DummyEvent]
        def depends_on(self): return [CritStage0]
        async def handle_event(self, e):
            DownstreamStage1.ran = True

    plan = PlanBuilder.build("DummyEvent", [CritStage0(), DownstreamStage1()])
    event = make_dummy_event()
    report = await ConsumerOrchestrator.run_plan(event, plan, uuid.uuid4())

    assert report.has_errors
    assert not DownstreamStage1.ran

    # Stage 0 result should be FAILED
    r0 = report.results[0]
    assert r0.consumer_name == "CritStage0"
    assert r0.status == ConsumerStatus.FAILED

    # Stage 1 result should be SKIPPED
    r1 = report.results[1]
    assert r1.consumer_name == "DownstreamStage1"
    assert r1.status == ConsumerStatus.SKIPPED
    assert r1.stage_index == 1


# ── Tests: Application Startup DAG Validation ────────────────────────────────

def test_startup_validation_all_plans():
    """Verify validate_and_log_startup_plans builds and validates cleanly."""
    reg = ConsumerRegistry()
    reg.register(DummyEvent, ConsumerA())
    reg.register(DummyEvent, ConsumerB())
    reg.register(DummyEvent, ConsumerC())

    plans = validate_and_log_startup_plans(reg)
    assert "DummyEvent" in plans
    assert plans["DummyEvent"].stage_count == 3
