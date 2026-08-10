from __future__ import annotations
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from dataclasses import FrozenInstanceError
from app.domain.journey.analytics.models import (
    AnalyticsObservationWindow, AnalyticsScope, ResidencyCategory,
    ProgressionPattern, TrendGranularity, OutcomeDataStatus,
    JourneyDistributionMetrics, StageAnalytics, TransitionAnalytics,
    TransitionSummaryMetrics, JourneyFunnelMetrics, JourneyFunnelStageMetrics,
    JourneyDurationMetrics, StageResidencyAnalytics, MaturityAnalytics,
    MomentumAnalytics, StabilityAnalytics, VelocityAnalytics,
    JourneyHealthAnalytics, ProgressionPatternAnalytics,
    ObservedStageOutcomeAnalytics, JourneyTrendPoint, JourneyTrendAnalytics,
    JourneyCohortDefinition, JourneyAnalyticsDiagnostics, JourneyAnalyticsProvenance,
)


class TestObservationWindow:
    def test_duration_days_correct(self):
        now = datetime.now(timezone.utc)
        window = AnalyticsObservationWindow(
            start_at=now - timedelta(days=30),
            end_at=now,
        )
        assert abs(window.duration_days - 30.0) < 0.01

    def test_zero_duration_safe(self):
        now = datetime.now(timezone.utc)
        window = AnalyticsObservationWindow(start_at=now, end_at=now)
        assert window.duration_days == 0.0

    def test_negative_duration_clamped(self):
        now = datetime.now(timezone.utc)
        # end before start
        window = AnalyticsObservationWindow(start_at=now, end_at=now - timedelta(days=1))
        assert window.duration_days == 0.0

    def test_is_frozen(self):
        now = datetime.now(timezone.utc)
        window = AnalyticsObservationWindow(start_at=now, end_at=now)
        with pytest.raises((FrozenInstanceError, AttributeError)):
            window.timezone = "America/New_York"  # type: ignore


class TestEnums:
    def test_analytics_scope_values(self):
        assert AnalyticsScope.WORKSPACE.value == "WORKSPACE"
        assert AnalyticsScope.COHORT.value == "COHORT"

    def test_residency_categories(self):
        assert ResidencyCategory.FAST_RESIDENCY.value == "FAST_RESIDENCY"
        assert ResidencyCategory.EXTENDED_RESIDENCY.value == "EXTENDED_RESIDENCY"

    def test_progression_patterns(self):
        assert ProgressionPattern.STALLED.value == "STALLED"
        assert ProgressionPattern.STEADY_PROGRESS.value == "STEADY_PROGRESS"

    def test_trend_granularity(self):
        assert TrendGranularity.DAILY.value == "DAILY"
        assert TrendGranularity.WEEKLY.value == "WEEKLY"
        assert TrendGranularity.MONTHLY.value == "MONTHLY"

    def test_outcome_data_status(self):
        assert OutcomeDataStatus.CALCULATED.value == "CALCULATED"
        assert OutcomeDataStatus.INSUFFICIENT_DATA.value == "INSUFFICIENT_DATA"


class TestFrozenDataclasses:
    def test_distribution_metrics_is_frozen(self):
        dm = JourneyDistributionMetrics(
            total_journeys=0, active_journeys=0, completed_journeys=0,
            cancelled_journeys=0, inactive_journeys=0, archived_journeys=0,
            by_journey_type={}, by_status={}, by_current_stage={},
            by_maturity_level={}, by_momentum_state={}, by_stability_level={},
            by_velocity_state={}, by_health_state={},
        )
        with pytest.raises((FrozenInstanceError, AttributeError)):
            dm.total_journeys = 5  # type: ignore

    def test_stage_analytics_is_frozen(self):
        sa = StageAnalytics(
            stage="NEW_LEAD", journey_count=5, percentage_of_journeys=50.0,
            unique_entries=5, unique_exits=3, current_residency_count=2,
            completed_residency_count=3, average_residency_days=5.0,
            median_residency_days=5.0, minimum_residency_days=1.0,
            maximum_residency_days=10.0, p25_residency_days=3.0, p75_residency_days=7.0,
        )
        with pytest.raises((FrozenInstanceError, AttributeError)):
            sa.journey_count = 10  # type: ignore

    def test_cohort_definition_is_frozen(self):
        cid = uuid.uuid4()
        cohort = JourneyCohortDefinition(
            cohort_id=cid,
            cohort_name="Test Cohort",
            workspace_id="ws-123",
        )
        with pytest.raises((FrozenInstanceError, AttributeError)):
            cohort.cohort_name = "Other"  # type: ignore
        assert cohort.cohort_id == cid
        assert cohort.cohort_name == "Test Cohort"
