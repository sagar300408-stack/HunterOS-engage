"""
Unit tests for Intent Evolution Event Stream and Timeline Projection Builders.
"""

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from app.domain.intents.evolution.models import (
    EntityType,
    IntentEvolutionEvent,
    IntentEvolutionEventStream,
    IntentEvolutionEventType,
    IntentLifecycleState,
    IntentStateSnapshot,
    IntentStateTransition,
    IntentVelocity,
)
from app.domain.intents.evolution.timelines.customer import CustomerTimelineBuilder
from app.domain.intents.evolution.timelines.deal import DealTimelineBuilder
from app.domain.intents.evolution.timelines.organization import OrganizationTimelineBuilder
from app.domain.intents.evolution.timelines.registry import IntentTimelineRegistry


def test_velocity_calculation():
    builder = CustomerTimelineBuilder()
    intent_id = uuid.uuid4()
    t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Less than 2 snapshots -> UNKNOWN
    snaps1 = [
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="c1",
            intent_type="Inquiry",
            category="Sales",
            taxonomy_path="Sales/Inquiry",
            observed_at=t0,
        )
    ]
    assert builder.calculate_velocity(snaps1) == IntentVelocity.UNKNOWN

    # 2. 2 snapshots -> STABLE
    snaps2 = snaps1 + [
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="c2",
            intent_type="Inquiry",
            category="Sales",
            taxonomy_path="Sales/Inquiry",
            observed_at=t0 + timedelta(days=2),
        )
    ]
    assert builder.calculate_velocity(snaps2) == IntentVelocity.STABLE

    # 3. 3 snapshots with shrinking intervals: 4 days then 1 day -> INCREASING
    snaps3 = [
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="c1",
            intent_type="Inquiry",
            category="Sales",
            taxonomy_path="Sales/Inquiry",
            observed_at=t0,
        ),
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="c2",
            intent_type="Inquiry",
            category="Sales",
            taxonomy_path="Sales/Inquiry",
            observed_at=t0 + timedelta(days=4),
        ),
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="cust-1",
            conversation_id="c3",
            intent_type="Inquiry",
            category="Sales",
            taxonomy_path="Sales/Inquiry",
            observed_at=t0 + timedelta(days=5), # 1 day interval
        ),
    ]
    assert builder.calculate_velocity(snaps3) == IntentVelocity.INCREASING


def test_timeline_builders_and_registry():
    registry = IntentTimelineRegistry()

    cust_builder = registry.get_builder(EntityType.CUSTOMER)
    org_builder = registry.get_builder(EntityType.ORGANIZATION)
    deal_builder = registry.get_builder(EntityType.DEAL)

    assert isinstance(cust_builder, CustomerTimelineBuilder)
    assert isinstance(org_builder, OrganizationTimelineBuilder)
    assert isinstance(deal_builder, DealTimelineBuilder)

    intent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    snaps = [
        IntentStateSnapshot(
            intent_id=intent_id,
            entity_id="org-500",
            conversation_id="c1",
            intent_type="EnterpriseSecurity",
            category="Security",
            taxonomy_path="Security/Compliance",
            observed_at=now,
            confidence=0.91,
        )
    ]
    events = [
        IntentEvolutionEvent(
            intent_id=intent_id,
            entity_type=EntityType.ORGANIZATION,
            entity_id="org-500",
            event_type=IntentEvolutionEventType.INTENT_CREATED,
            current_state=IntentLifecycleState.NEW,
            occurred_at=now,
        )
    ]

    timeline = org_builder.build_timeline(
        intent_id=intent_id,
        entity_id="org-500",
        snapshots=snaps,
        events=events,
        transitions=[],
    )

    assert timeline.entity_type == EntityType.ORGANIZATION
    assert timeline.entity_id == "org-500"
    assert timeline.current_lifecycle_state == IntentLifecycleState.NEW
    assert timeline.observation_frequency == 1
