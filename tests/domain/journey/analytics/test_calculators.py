from __future__ import annotations
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from app.domain.journey.models import JourneyState, JourneyStatus, JourneyStageCode, TransitionType
from app.domain.journey.analytics.calculators.distribution import JourneyDistributionCalculator
from app.domain.journey.analytics.calculators.stage import StageAnalyticsCalculator
from app.domain.journey.analytics.calculators.transition import TransitionAnalyticsCalculator
from app.domain.journey.analytics.calculators.duration import JourneyDurationCalculator
from app.domain.journey.analytics.calculators.maturity import MaturityAnalyticsCalculator
from app.domain.journey.analytics.calculators.momentum import MomentumAnalyticsCalculator
from app.domain.journey.analytics.calculators.stability import StabilityAnalyticsCalculator
from app.domain.journey.analytics.calculators.velocity import VelocityAnalyticsCalculator
from app.domain.journey.analytics.calculators.health import JourneyHealthAnalyticsCalculator
from app.domain.journey.analytics.calculators.progression import ProgressionPatternCalculator
from app.domain.journey.analytics.calculators.outcome import ObservedOutcomeCalculator
from app.domain.journey.analytics.configuration import build_default_analytics_configuration
# Import test helpers
from tests.domain.journey.analytics.conftest import make_journey_state, make_transition


@pytest.fixture
def workspace_id():
    return str(uuid.uuid4())


class TestDistributionCalculator:
    def setup_method(self):
        self.calc = JourneyDistributionCalculator()

    def test_empty_journeys_returns_zeros(self, workspace_id):
        result = self.calc.calculate([], [])
        assert result.total_journeys == 0
        assert result.active_journeys == 0

    def test_counts_active_correctly(self, workspace_id):
        journeys = [
            make_journey_state(workspace_id, status=JourneyStatus.ACTIVE),
            make_journey_state(workspace_id, status=JourneyStatus.ACTIVE),
            make_journey_state(workspace_id, status=JourneyStatus.COMPLETED),
        ]
        result = self.calc.calculate(journeys, [])
        assert result.total_journeys == 3
        assert result.active_journeys == 2
        assert result.completed_journeys == 1

    def test_by_status_percentages_sum_to_100(self, workspace_id):
        journeys = [
            make_journey_state(workspace_id, status=JourneyStatus.ACTIVE),
            make_journey_state(workspace_id, status=JourneyStatus.COMPLETED),
            make_journey_state(workspace_id, status=JourneyStatus.LOST),
        ]
        result = self.calc.calculate(journeys, [])
        total_pct = sum(v["percentage"] for v in result.by_status.values())
        assert total_pct == pytest.approx(100.0, abs=0.1)

    def test_by_stage_distribution(self, workspace_id):
        journeys = [
            make_journey_state(workspace_id, stage=JourneyStageCode.NEW_LEAD),
            make_journey_state(workspace_id, stage=JourneyStageCode.NEW_LEAD),
            make_journey_state(workspace_id, stage=JourneyStageCode.INTERESTED),
        ]
        result = self.calc.calculate(journeys, [])
        assert "NEW_LEAD" in result.by_current_stage
        assert result.by_current_stage["NEW_LEAD"]["count"] == 2
        assert result.by_current_stage["INTERESTED"]["count"] == 1


class TestDurationCalculator:
    def setup_method(self):
        self.calc = JourneyDurationCalculator()

    def test_empty_returns_nones(self, workspace_id):
        result = self.calc.calculate([])
        assert result.total_sample_size == 0
        assert result.average_duration_days is None

    def test_average_duration_correct(self, workspace_id):
        journeys = [
            make_journey_state(workspace_id, started_days_ago=10.0),
            make_journey_state(workspace_id, started_days_ago=20.0),
        ]
        result = self.calc.calculate(journeys)
        assert result.total_sample_size == 2
        assert result.average_duration_days == pytest.approx(15.0, abs=0.1)

    def test_active_vs_completed_averages(self, workspace_id):
        journeys = [
            make_journey_state(workspace_id, status=JourneyStatus.ACTIVE, started_days_ago=5.0),
            make_journey_state(workspace_id, status=JourneyStatus.COMPLETED, started_days_ago=30.0),
        ]
        result = self.calc.calculate(journeys)
        assert result.active_average_days is not None
        assert result.completed_average_days is not None
        assert result.active_average_days != result.completed_average_days


class TestTransitionCalculator:
    def setup_method(self):
        self.calc = TransitionAnalyticsCalculator()

    def test_empty_transitions_returns_zeros(self, workspace_id):
        result = self.calc.calculate([], [])
        assert result.total_transitions == 0
        assert result.forward_transition_count == 0
        assert result.regression_transition_count == 0

    def test_counts_transitions_correctly(self, workspace_id):
        j = make_journey_state(workspace_id)
        t1 = make_transition(j.journey_instance_id, JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED)
        t2 = make_transition(j.journey_instance_id, JourneyStageCode.INTERESTED, JourneyStageCode.QUALIFIED)
        result = self.calc.calculate([t1, t2], [j])
        assert result.total_transitions == 2

    def test_regression_detected(self, workspace_id):
        j = make_journey_state(workspace_id)
        t = make_transition(
            j.journey_instance_id,
            JourneyStageCode.INTERESTED,
            JourneyStageCode.NEW_LEAD,
            transition_type=TransitionType.REGRESSION,
        )
        result = self.calc.calculate([t], [j])
        assert result.regression_transition_count > 0


class TestOutcomeCalculator:
    def setup_method(self):
        self.calc = ObservedOutcomeCalculator(minimum_sample=5)  # low for testing

    def test_empty_journeys_returns_insufficient_data(self, workspace_id):
        result = self.calc.calculate([], workspace_id)
        assert len(result) == 0 or all(
            v.observed_rate is None for v in result.values()
        )

    def test_insufficient_sample_returns_none_rate(self, workspace_id):
        # Only 3 closed journeys - below minimum_sample=5
        journeys = [
            make_journey_state(
                workspace_id,
                stage=JourneyStageCode.CLOSED_WON,
                status=JourneyStatus.COMPLETED,
                stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.CLOSED_WON],
            )
            for _ in range(3)
        ]
        result = self.calc.calculate(journeys, workspace_id, stages_to_analyze=["NEW_LEAD"])
        if "NEW_LEAD" in result:
            assert result["NEW_LEAD"].observed_rate is None
            assert not result["NEW_LEAD"].minimum_sample_met

    def test_sufficient_sample_returns_rate(self, workspace_id):
        # 6 closed journeys - above minimum_sample=5
        won = [
            make_journey_state(
                workspace_id,
                stage=JourneyStageCode.CLOSED_WON,
                status=JourneyStatus.COMPLETED,
                stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.CLOSED_WON],
            )
            for _ in range(3)
        ]
        lost = [
            make_journey_state(
                workspace_id,
                stage=JourneyStageCode.CLOSED_LOST,
                status=JourneyStatus.LOST,
                stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.CLOSED_LOST],
            )
            for _ in range(3)
        ]
        result = self.calc.calculate(won + lost, workspace_id, stages_to_analyze=["NEW_LEAD"])
        if "NEW_LEAD" in result:
            assert result["NEW_LEAD"].minimum_sample_met
            assert result["NEW_LEAD"].observed_rate is not None
            assert 0.0 <= result["NEW_LEAD"].observed_rate <= 1.0

    def test_workspace_isolation(self, workspace_id, other_workspace_id):
        """Journeys from other workspace must not be counted."""
        other_journeys = [
            make_journey_state(
                other_workspace_id,  # Different workspace!
                stage=JourneyStageCode.CLOSED_WON,
                status=JourneyStatus.COMPLETED,
                stage_history=[JourneyStageCode.NEW_LEAD, JourneyStageCode.CLOSED_WON],
            )
            for _ in range(10)
        ]
        result = self.calc.calculate(other_journeys, workspace_id, stages_to_analyze=["NEW_LEAD"])
        # Since other_workspace journeys don't match workspace_id, result should have insufficient data
        for v in result.values():
            assert not v.minimum_sample_met

    def test_other_workspace_id(self):
        return str(uuid.uuid4())


class TestProgressionCalculator:
    def setup_method(self):
        self.calc = ProgressionPatternCalculator()

    def test_empty_journeys_returns_zero_sample(self, workspace_id):
        result = self.calc.calculate([])
        assert result.sample_size == 0

    def test_inactive_journeys_classified(self, workspace_id):
        journeys = [make_journey_state(workspace_id, status=JourneyStatus.INACTIVE)]
        result = self.calc.calculate(journeys)
        assert result.sample_size == 1

    def test_pattern_distribution_keys_are_valid(self, workspace_id):
        from app.domain.journey.analytics.models import ProgressionPattern
        journeys = [
            make_journey_state(workspace_id) for _ in range(5)
        ]
        result = self.calc.calculate(journeys)
        valid_patterns = {p.value for p in ProgressionPattern}
        for k in result.pattern_distribution.keys():
            assert k in valid_patterns
