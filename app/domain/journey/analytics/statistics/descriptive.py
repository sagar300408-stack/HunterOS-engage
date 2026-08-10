"""
HunterOS Engage V1 — Journey Analytics
Phase 2.4.4: Descriptive Statistics Engine

Pure statistical calculations. No ML. No predictions. Deterministic.
Handles empty datasets, single-item datasets, zero denominators safely.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional


class DescriptiveStatisticsEngine:
    """Deterministic descriptive statistics without external dependencies."""

    def mean(self, values: List[float]) -> Optional[float]:
        if not values:
            return None
        return sum(values) / len(values)

    def median(self, values: List[float]) -> Optional[float]:
        if not values:
            return None
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
        return float(sorted_vals[mid])

    def minimum(self, values: List[float]) -> Optional[float]:
        return min(values) if values else None

    def maximum(self, values: List[float]) -> Optional[float]:
        return max(values) if values else None

    def percentile(self, values: List[float], p: float) -> Optional[float]:
        """Linear interpolation percentile. p in [0, 100]."""
        if not values:
            return None
        if len(values) == 1:
            return float(values[0])
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        # Linear interpolation
        idx = (p / 100.0) * (n - 1)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return float(sorted_vals[lo])
        fraction = idx - lo
        return sorted_vals[lo] + fraction * (sorted_vals[hi] - sorted_vals[lo])

    def std_dev(self, values: List[float]) -> Optional[float]:
        if len(values) < 2:
            return None
        m = self.mean(values)
        if m is None:
            return None
        variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)  # sample std dev
        return math.sqrt(variance)

    def count(self, values: List) -> int:
        return len(values)

    def safe_percentage(self, numerator: int, denominator: int) -> float:
        """Safe percentage calculation. Returns 0.0 for zero denominator."""
        if denominator == 0:
            return 0.0
        return round((numerator / denominator) * 100.0, 4)

    def safe_ratio(self, numerator: float, denominator: float) -> float:
        """Safe ratio (0.0-1.0). Returns 0.0 for zero denominator."""
        if denominator == 0.0:
            return 0.0
        return min(1.0, max(0.0, numerator / denominator))

    def distribution_percentages(
        self, counts: Dict[str, int], total: Optional[int] = None
    ) -> Dict[str, float]:
        """Convert count dict to percentage dict. Safe against zero denominator."""
        if total is None:
            total = sum(counts.values())
        if total == 0:
            return {k: 0.0 for k in counts}
        return {
            k: round((v / total) * 100.0, 4)
            for k, v in counts.items()
        }

    def summarize(self, values: List[float]) -> Dict[str, Optional[float]]:
        """Return full descriptive summary dict."""
        return {
            "count": float(len(values)),
            "mean": self.mean(values),
            "median": self.median(values),
            "min": self.minimum(values),
            "max": self.maximum(values),
            "p25": self.percentile(values, 25),
            "p75": self.percentile(values, 75),
            "std_dev": self.std_dev(values),
        }


default_stats_engine: DescriptiveStatisticsEngine = DescriptiveStatisticsEngine()
