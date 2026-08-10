from __future__ import annotations
import pytest
from app.domain.journey.analytics.statistics.descriptive import DescriptiveStatisticsEngine
from app.domain.journey.analytics.statistics.confidence import calculate_proportion_ci, ConfidenceInterval


class TestDescriptiveStatisticsEngine:
    def setup_method(self):
        self.stats = DescriptiveStatisticsEngine()

    def test_mean_empty_returns_none(self):
        assert self.stats.mean([]) is None

    def test_mean_single(self):
        assert self.stats.mean([5.0]) == 5.0

    def test_mean_multiple(self):
        result = self.stats.mean([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result == pytest.approx(3.0)

    def test_median_empty_returns_none(self):
        assert self.stats.median([]) is None

    def test_median_odd_count(self):
        assert self.stats.median([1.0, 3.0, 5.0]) == 3.0

    def test_median_even_count(self):
        assert self.stats.median([1.0, 2.0, 3.0, 4.0]) == pytest.approx(2.5)

    def test_minimum_empty_returns_none(self):
        assert self.stats.minimum([]) is None

    def test_minimum_correct(self):
        assert self.stats.minimum([5.0, 3.0, 8.0, 1.0]) == 1.0

    def test_maximum_correct(self):
        assert self.stats.maximum([5.0, 3.0, 8.0, 1.0]) == 8.0

    def test_percentile_empty_returns_none(self):
        assert self.stats.percentile([], 50) is None

    def test_percentile_p50_is_median(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert self.stats.percentile(vals, 50) == self.stats.median(vals)

    def test_percentile_p25(self):
        vals = [1.0, 2.0, 3.0, 4.0]
        result = self.stats.percentile(vals, 25)
        assert result is not None
        assert 1.0 <= result <= 2.0

    def test_safe_percentage_zero_denominator(self):
        assert self.stats.safe_percentage(5, 0) == 0.0

    def test_safe_percentage_normal(self):
        assert self.stats.safe_percentage(5, 10) == pytest.approx(50.0)

    def test_safe_ratio_zero_denominator(self):
        assert self.stats.safe_ratio(5.0, 0.0) == 0.0

    def test_safe_ratio_normal(self):
        assert self.stats.safe_ratio(3.0, 10.0) == pytest.approx(0.3)

    def test_safe_ratio_capped_at_1(self):
        assert self.stats.safe_ratio(20.0, 10.0) == 1.0

    def test_distribution_percentages_zero_total(self):
        result = self.stats.distribution_percentages({"A": 0, "B": 0})
        assert result == {"A": 0.0, "B": 0.0}

    def test_distribution_percentages_normal(self):
        result = self.stats.distribution_percentages({"A": 3, "B": 7}, total=10)
        assert result["A"] == pytest.approx(30.0)
        assert result["B"] == pytest.approx(70.0)

    def test_std_dev_single_returns_none(self):
        assert self.stats.std_dev([5.0]) is None

    def test_std_dev_correct(self):
        # sample std dev (ddof=1) of [2, 4, 4, 4, 5, 5, 7, 9] ≈ 2.138
        result = self.stats.std_dev([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        assert result is not None
        assert result == pytest.approx(2.138, rel=0.01)

    def test_summarize_returns_all_keys(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = self.stats.summarize(vals)
        assert "mean" in result
        assert "median" in result
        assert "min" in result
        assert "max" in result
        assert "p25" in result
        assert "p75" in result
        assert "std_dev" in result

    def test_summarize_empty_returns_nones(self):
        result = self.stats.summarize([])
        assert result["mean"] is None
        assert result["median"] is None


class TestWilsonConfidenceInterval:
    def test_zero_sample_returns_zeros(self):
        ci = calculate_proportion_ci(0, 0)
        assert ci.point_estimate == 0.0
        assert ci.lower_bound == 0.0
        assert ci.upper_bound == 0.0
        assert not ci.satisfied_minimum_sample

    def test_all_successes(self):
        ci = calculate_proportion_ci(30, 30, minimum_sample=30)
        assert ci.point_estimate == 1.0
        assert ci.lower_bound <= ci.point_estimate
        assert ci.upper_bound <= 1.0
        assert ci.satisfied_minimum_sample

    def test_no_successes(self):
        ci = calculate_proportion_ci(0, 30, minimum_sample=30)
        assert ci.point_estimate == 0.0
        assert ci.lower_bound >= 0.0
        assert ci.satisfied_minimum_sample

    def test_half_successes(self):
        ci = calculate_proportion_ci(15, 30, minimum_sample=30)
        assert ci.point_estimate == pytest.approx(0.5, abs=0.01)
        assert ci.lower_bound < 0.5
        assert ci.upper_bound > 0.5

    def test_below_minimum_sample_not_satisfied(self):
        ci = calculate_proportion_ci(10, 20, minimum_sample=30)
        assert not ci.satisfied_minimum_sample

    def test_deterministic(self):
        ci1 = calculate_proportion_ci(15, 30)
        ci2 = calculate_proportion_ci(15, 30)
        assert ci1.point_estimate == ci2.point_estimate
        assert ci1.lower_bound == ci2.lower_bound
        assert ci1.upper_bound == ci2.upper_bound

    def test_bounds_within_0_1(self):
        for successes in [0, 5, 15, 25, 30]:
            ci = calculate_proportion_ci(successes, 30)
            assert 0.0 <= ci.lower_bound <= 1.0
            assert 0.0 <= ci.upper_bound <= 1.0
