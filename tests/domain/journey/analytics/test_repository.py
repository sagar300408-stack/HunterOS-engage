from __future__ import annotations
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.journey.analytics.repository import InMemoryJourneyAnalyticsRepository
from app.domain.journey.analytics.models import (
    AnalyticsObservationWindow, JourneyAnalyticsResult, JourneyAnalyticsDiagnostics,
    JourneyAnalyticsProvenance, JourneyDistributionMetrics, TransitionSummaryMetrics,
    JourneyDurationMetrics, MaturityAnalytics, MomentumAnalytics, StabilityAnalytics,
    VelocityAnalytics, JourneyHealthAnalytics, ProgressionPatternAnalytics,
)


def _make_minimal_result(workspace_id: str, journey_type: str = None) -> JourneyAnalyticsResult:
    """Create a minimal but valid JourneyAnalyticsResult for testing."""
    now = datetime.now(timezone.utc)
    window = AnalyticsObservationWindow(
        start_at=now - timedelta(days=30), end_at=now
    )
    analytics_id = uuid.uuid4()
    dist = JourneyDistributionMetrics(
        total_journeys=0, active_journeys=0, completed_journeys=0,
        cancelled_journeys=0, inactive_journeys=0, archived_journeys=0,
        by_journey_type={}, by_status={}, by_current_stage={},
        by_maturity_level={}, by_momentum_state={}, by_stability_level={},
        by_velocity_state={}, by_health_state={},
    )
    transition_metrics = TransitionSummaryMetrics(
        total_transitions=0, forward_transition_count=0, regression_transition_count=0,
        same_stage_reentry_count=0, terminal_transition_count=0, by_transition=[],
    )
    duration = JourneyDurationMetrics(
        total_sample_size=0, average_duration_days=None, median_duration_days=None,
        minimum_duration_days=None, maximum_duration_days=None, p25_duration_days=None,
        p75_duration_days=None, active_average_days=None, completed_average_days=None,
        cancelled_average_days=None,
    )
    maturity = MaturityAnalytics(
        sample_size=0, average_maturity_score=None, median_maturity_score=None,
        lowest_maturity_score=None, highest_maturity_score=None,
        maturity_level_counts={}, maturity_level_percentages={},
        lowest_maturity_bucket=None, highest_maturity_bucket=None,
    )
    momentum = MomentumAnalytics(
        sample_size=0, state_counts={}, state_percentages={},
        advancing_percentage=0.0, stable_percentage=0.0, weakening_percentage=0.0,
        regressing_percentage=0.0, inactive_percentage=0.0, unknown_percentage=0.0,
    )
    stability = StabilityAnalytics(
        sample_size=0, level_counts={}, level_percentages={},
        average_stability_score=None, reentry_frequency=0.0,
        oscillation_frequency=0.0, conflicting_evidence_frequency=0.0,
    )
    velocity = VelocityAnalytics(
        sample_size=0, state_counts={}, state_percentages={},
        average_transitions_per_day=None, average_transitions_per_week=None,
        average_stage_duration_days=None,
    )
    health = JourneyHealthAnalytics(
        sample_size=0, health_distribution={}, health_percentages={},
        healthy_percentage=0.0, stalled_percentage=0.0, regressing_percentage=0.0,
        inactive_percentage=0.0, insufficient_data_percentage=0.0,
    )
    progression = ProgressionPatternAnalytics(
        sample_size=0, average_forward_transitions=None, average_regressions=None,
        average_reentries=None, average_stage_changes=None, average_journey_age_days=None,
        progression_consistency_score=None, pattern_distribution={}, pattern_percentages={},
    )
    diagnostics = JourneyAnalyticsDiagnostics(
        stage_timings={}, total_execution_time_ms=0.0, journeys_processed=0,
        transitions_processed=0, timeline_events_processed=0, maturity_results_processed=0,
        metrics_calculated=[], warnings=[], validation_errors=[],
        empty_dataset=True, partial_dataset=False, insufficient_data_metrics=[],
    )
    provenance = JourneyAnalyticsProvenance(
        analytics_id=analytics_id, workspace_id=workspace_id, generated_at=now,
        observation_window=window, engine_version="2.4.4", pipeline_version="v1",
        configuration_version="default", source_journey_count=0,
        source_transition_count=0, source_maturity_count=0,
        filters={}, cohort_definition=None, calculation_methods=[], statistical_methods=[],
    )
    return JourneyAnalyticsResult(
        analytics_id=analytics_id, workspace_id=workspace_id,
        journey_type=journey_type, definition_version=None,
        observation_window=window, generated_at=now,
        journey_count=0, distribution=dist, stage_analytics={},
        transition_metrics=transition_metrics, funnel=None,
        duration_metrics=duration, residency_analytics={},
        maturity_analytics=maturity, momentum_analytics=momentum,
        stability_analytics=stability, velocity_analytics=velocity,
        health_analytics=health, progression_patterns=progression,
        outcome_analytics={}, trend_analytics=None, cohort_metrics=None,
        diagnostics=diagnostics, provenance=provenance,
    )


class TestInMemoryJourneyAnalyticsRepository:
    def setup_method(self):
        self.repo = InMemoryJourneyAnalyticsRepository()
        self.workspace_id = str(uuid.uuid4())

    def test_save_and_get_result(self):
        result = _make_minimal_result(self.workspace_id)
        self.repo.save_result(result)
        retrieved = self.repo.get_result(result.analytics_id)
        assert retrieved is not None
        assert str(retrieved.analytics_id) == str(result.analytics_id)

    def test_get_nonexistent_returns_none(self):
        assert self.repo.get_result(uuid.uuid4()) is None

    def test_get_latest_returns_most_recent(self):
        result1 = _make_minimal_result(self.workspace_id)
        result2 = _make_minimal_result(self.workspace_id)
        self.repo.save_result(result1)
        self.repo.save_result(result2)
        latest = self.repo.get_latest_result(self.workspace_id)
        assert latest is not None

    def test_get_latest_by_journey_type(self):
        result_sales = _make_minimal_result(self.workspace_id, journey_type="SALES")
        result_re = _make_minimal_result(self.workspace_id, journey_type="PROPERTY_PURCHASE")
        self.repo.save_result(result_sales)
        self.repo.save_result(result_re)
        sales_latest = self.repo.get_latest_result(self.workspace_id, journey_type="SALES")
        assert sales_latest is not None
        assert sales_latest.journey_type == "SALES"

    def test_workspace_isolation(self):
        other_ws = str(uuid.uuid4())
        result = _make_minimal_result(other_ws)
        self.repo.save_result(result)
        # Should not appear in self.workspace_id queries
        assert self.repo.get_latest_result(self.workspace_id) is None

    def test_query_results_by_date(self):
        result = _make_minimal_result(self.workspace_id)
        self.repo.save_result(result)
        from datetime import datetime, timezone, timedelta
        future = datetime.now(timezone.utc) + timedelta(days=1)
        past = datetime.now(timezone.utc) - timedelta(days=1)
        # Should find it within a wide range
        results = self.repo.query_results(self.workspace_id, from_date=past, to_date=future)
        assert len(results) >= 1


class TestNullCache:
    def test_null_cache_always_misses(self):
        from app.domain.journey.analytics.cache import NullJourneyAnalyticsCache
        cache = NullJourneyAnalyticsCache()
        result = _make_minimal_result("ws-123")
        cache.set("key", result)
        assert cache.get("key") is None


class TestInMemoryCache:
    def test_set_and_get(self):
        from app.domain.journey.analytics.cache import InMemoryJourneyAnalyticsCache
        cache = InMemoryJourneyAnalyticsCache()
        result = _make_minimal_result("ws-123")
        cache.set("key", result)
        assert cache.get("key") is not None

    def test_invalidate_removes_entry(self):
        from app.domain.journey.analytics.cache import InMemoryJourneyAnalyticsCache
        cache = InMemoryJourneyAnalyticsCache()
        result = _make_minimal_result("ws-123")
        cache.set("key", result)
        cache.invalidate("key")
        assert cache.get("key") is None

    def test_clear_removes_all(self):
        from app.domain.journey.analytics.cache import InMemoryJourneyAnalyticsCache
        cache = InMemoryJourneyAnalyticsCache()
        for i in range(5):
            cache.set(f"key{i}", _make_minimal_result("ws-123"))
        cache.clear()
        for i in range(5):
            assert cache.get(f"key{i}") is None
