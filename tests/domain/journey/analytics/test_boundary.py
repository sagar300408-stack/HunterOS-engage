from __future__ import annotations
import inspect
import pytest


class TestAnalyticsBoundaryInvariants:
    """Verify strict architectural invariants for the analytics layer."""

    def test_engine_never_imports_write_intent(self):
        """Analytics engine must not import or reference intent write operations."""
        import app.domain.journey.analytics.engine as engine_module
        source = inspect.getsource(engine_module)
        # Should not import write/mutation operations from intent domain
        assert "intent_api_v1.write" not in source
        assert "intent_api_v1.create" not in source

    def test_engine_does_not_mutate_journey_state(self):
        """Engine source must not call save_journey_state or create_journey."""
        import app.domain.journey.analytics.engine as engine_module
        source = inspect.getsource(engine_module)
        assert "save_journey_state" not in source
        assert "create_journey" not in source

    def test_engine_has_no_recommend_methods(self):
        """No recommendation generation in analytics engine."""
        import app.domain.journey.analytics.engine as engine_module
        source = inspect.getsource(engine_module)
        # These words must not appear as method names or concepts
        assert "recommend" not in source.lower()
        assert "next_best_action" not in source.lower()
        assert "next_stage" not in source.lower()

    def test_models_are_all_frozen(self):
        """All analytics domain models must be frozen dataclasses."""
        import dataclasses
        import app.domain.journey.analytics.models as models_module

        for name, obj in inspect.getmembers(models_module, inspect.isclass):
            if dataclasses.is_dataclass(obj) and obj.__module__ == models_module.__name__:
                fields = dataclasses.fields(obj)
                # If it has fields, it should be frozen
                if fields:
                    assert obj.__dataclass_params__.frozen, (
                        f"{name} is a dataclass but is NOT frozen. All analytics models must be frozen."
                    )

    def test_calculators_do_not_predict(self):
        """All calculator source files must not define predictive operations.

        Negations in docstrings (e.g. 'no prediction', 'strictly historical')
        are allowable; we check for actual predictive method/attribute names.
        """
        import importlib
        import re
        # Patterns that would indicate actual predictive intent (not negations)
        bad_patterns = [
            r'def predict_',
            r'def forecast_',
            r'def recommend_',
            r'def score_lead',
            r'next_best_action',
            r'lead_score',
        ]
        calculator_names = [
            "distribution", "stage", "transition", "funnel", "duration",
            "residency", "maturity", "momentum", "stability", "velocity",
            "health", "outcome", "trends", "cohort", "progression",
        ]
        for name in calculator_names:
            try:
                mod = importlib.import_module(f"app.domain.journey.analytics.calculators.{name}")
                source = inspect.getsource(mod)
                for pattern in bad_patterns:
                    assert not re.search(pattern, source, re.IGNORECASE), (
                        f"{name}.py contains disallowed predictive pattern: '{pattern}'"
                    )
            except ImportError:
                pass

    def test_statistics_engine_is_deterministic(self):
        """Same inputs to statistics engine must produce same outputs."""
        from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine
        stats = DescriptiveStatisticsEngine()
        vals = [1.0, 3.0, 5.0, 7.0, 9.0]

        result1 = stats.summarize(vals)
        result2 = stats.summarize(vals)
        assert result1 == result2

    def test_confidence_interval_deterministic(self):
        """Same inputs to Wilson CI must produce same outputs."""
        from app.domain.journey.analytics.statistics.confidence import calculate_proportion_ci
        ci1 = calculate_proportion_ci(15, 30)
        ci2 = calculate_proportion_ci(15, 30)
        assert ci1.point_estimate == ci2.point_estimate
        assert ci1.lower_bound == ci2.lower_bound
        assert ci1.upper_bound == ci2.upper_bound
