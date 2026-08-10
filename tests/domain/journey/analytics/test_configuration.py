from __future__ import annotations
import pytest
from app.domain.journey.analytics.configuration import (
    JourneyAnalyticsConfiguration,
    JourneyAnalyticsConfigurationRegistry,
    build_default_analytics_configuration,
    default_analytics_config_registry,
)
from app.domain.journey.analytics.models import ResidencyCategory, TrendGranularity


class TestJourneyAnalyticsConfiguration:
    def test_build_default_has_correct_version(self):
        cfg = build_default_analytics_configuration()
        assert cfg.version == "analytics-v1"

    def test_default_observation_window_is_365(self):
        cfg = build_default_analytics_configuration()
        assert cfg.default_observation_window_days == 365

    def test_metric_enabled_when_list_empty(self):
        cfg = build_default_analytics_configuration()
        assert cfg.is_metric_enabled("distribution")
        assert cfg.is_metric_enabled("anything")

    def test_metric_disabled_when_not_in_list(self):
        cfg = JourneyAnalyticsConfiguration(
            version="test-v1",
            enabled_metrics=["distribution", "funnel"],
        )
        assert cfg.is_metric_enabled("distribution")
        assert not cfg.is_metric_enabled("maturity")

    def test_residency_category_fast(self):
        cfg = build_default_analytics_configuration()
        assert cfg.get_residency_category(1.0) == ResidencyCategory.FAST_RESIDENCY

    def test_residency_category_normal(self):
        cfg = build_default_analytics_configuration()
        assert cfg.get_residency_category(7.0) == ResidencyCategory.NORMAL_RESIDENCY

    def test_residency_category_slow(self):
        cfg = build_default_analytics_configuration()
        assert cfg.get_residency_category(20.0) == ResidencyCategory.SLOW_RESIDENCY

    def test_residency_category_extended(self):
        cfg = build_default_analytics_configuration()
        assert cfg.get_residency_category(60.0) == ResidencyCategory.EXTENDED_RESIDENCY


class TestConfigurationRegistry:
    def test_default_registry_has_default(self):
        cfg = default_analytics_config_registry.resolve()
        assert cfg is not None
        assert cfg.version == "analytics-v1"

    def test_register_and_get(self):
        reg = JourneyAnalyticsConfigurationRegistry()
        custom = JourneyAnalyticsConfiguration(version="custom-v1")
        reg.register(custom)
        retrieved = reg.get("custom-v1")
        assert retrieved is not None
        assert retrieved.version == "custom-v1"

    def test_resolve_missing_returns_default(self):
        reg = JourneyAnalyticsConfigurationRegistry()
        result = reg.resolve("nonexistent-version")
        assert result is not None

    def test_list_returns_all(self):
        reg = JourneyAnalyticsConfigurationRegistry()
        configs = reg.list()
        assert len(configs) >= 1

    def test_thread_safety(self):
        import threading
        reg = JourneyAnalyticsConfigurationRegistry()
        errors = []

        def register_config(i: int):
            try:
                cfg = JourneyAnalyticsConfiguration(version=f"v{i}")
                reg.register(cfg, set_as_default=False)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_config, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
