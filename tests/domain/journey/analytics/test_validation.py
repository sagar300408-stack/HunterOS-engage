from __future__ import annotations
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.journey.analytics.validation import JourneyAnalyticsValidator
from app.domain.journey.analytics.models import AnalyticsObservationWindow
from tests.domain.journey.analytics.conftest import make_journey_state


class TestJourneyAnalyticsValidator:
    def setup_method(self):
        self.validator = JourneyAnalyticsValidator()
        self.workspace_id = str(uuid.uuid4())
        self.other_ws = str(uuid.uuid4())

    def test_workspace_isolation_passes_same_workspace(self):
        journeys = [make_journey_state(self.workspace_id) for _ in range(3)]
        errors = self.validator.validate_workspace_isolation(journeys, self.workspace_id)
        assert errors == []

    def test_workspace_isolation_fails_different_workspace(self):
        journeys = [make_journey_state(self.other_ws)]  # Wrong workspace
        errors = self.validator.validate_workspace_isolation(journeys, self.workspace_id)
        assert len(errors) > 0
        assert any("isolation" in e.lower() or "workspace" in e.lower() for e in errors)

    def test_observation_window_valid(self):
        now = datetime.now(timezone.utc)
        window = AnalyticsObservationWindow(start_at=now - timedelta(days=30), end_at=now)
        warnings = self.validator.validate_observation_window(window)
        assert warnings == []

    def test_observation_window_inverted_fails(self):
        now = datetime.now(timezone.utc)
        window = AnalyticsObservationWindow(start_at=now, end_at=now - timedelta(days=1))
        warnings = self.validator.validate_observation_window(window)
        assert len(warnings) > 0

    def test_duplicate_journeys_detected(self):
        j = make_journey_state(self.workspace_id)
        errors = self.validator.validate_duplicate_journeys([j, j])  # Same object twice
        assert len(errors) > 0

    def test_no_duplicates_passes(self):
        journeys = [make_journey_state(self.workspace_id) for _ in range(5)]
        errors = self.validator.validate_duplicate_journeys(journeys)
        assert errors == []

    def test_percentage_bounds_valid(self):
        pcts = {"A": 30.0, "B": 70.0}
        warnings = self.validator.validate_percentage_bounds(pcts, "test")
        assert warnings == []

    def test_percentage_bounds_deviation(self):
        pcts = {"A": 30.0, "B": 30.0}  # Only sums to 60
        warnings = self.validator.validate_percentage_bounds(pcts, "test")
        assert len(warnings) > 0

    def test_probability_in_bounds_valid(self):
        warnings = self.validator.validate_probability_bounds(0.5, "test")
        assert warnings == []

    def test_probability_out_of_bounds_flagged(self):
        warnings = self.validator.validate_probability_bounds(1.5, "test")
        assert len(warnings) > 0

    def test_none_probability_no_warnings(self):
        warnings = self.validator.validate_probability_bounds(None, "test")
        assert warnings == []
