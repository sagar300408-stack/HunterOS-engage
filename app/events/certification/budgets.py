"""
HunterOS Engage — Deterministic Performance Budgets
app/events/certification/budgets.py

Defines performance metrics collectors, percentile estimators, and deterministic
budget enforcement validators. Fails certification if any budget is breached.
"""

import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from app.events.certification.config import PerformanceBudgets, certification_config


@dataclass
class BudgetMetricReport:
    """Detailed percentile report for a single operation budget."""
    metric_name: str
    sample_count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    budget_limit_ms: float
    passed: bool
    details: str = ""


@dataclass
class PerformanceCertificationResult:
    """Overall certification outcome across all enforced budgets."""
    passed: bool
    total_samples: int
    reports: Dict[str, BudgetMetricReport] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)


class PerformanceBudgetTracker:
    """
    Records operational latencies and validates adherence to deterministic budgets.
    """

    def __init__(self, budgets: Optional[PerformanceBudgets] = None):
        self._budgets = budgets or certification_config.budgets
        self._samples: Dict[str, List[float]] = {
            "event_publish": [],
            "dispatcher_planning": [],
            "consumer_planning": [],
            "worker_overhead": [],
            "trace_overhead": [],
            "scheduler_planning_10k": [],
        }

    def record(self, metric_name: str, duration_ms: float) -> None:
        """Record a single latency sample in milliseconds."""
        if metric_name not in self._samples:
            self._samples[metric_name] = []
        self._samples[metric_name].append(max(0.0, float(duration_ms)))

    def record_samples(self, metric_name: str, durations_ms: List[float]) -> None:
        """Record a batch of latency samples in milliseconds."""
        for d in durations_ms:
            self.record(metric_name, d)

    def _compute_percentile(self, sorted_data: List[float], percentile: float) -> float:
        """Compute the given percentile (0-100) using linear interpolation."""
        if not sorted_data:
            return 0.0
        n = len(sorted_data)
        if n == 1:
            return sorted_data[0]
        k = (n - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_data[int(k)]
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return d0 + d1

    def evaluate_metric(self, metric_name: str, limit_ms: float, use_p95: bool = True) -> BudgetMetricReport:
        """Compute statistics and evaluate budget pass/fail for a metric."""
        samples = self._samples.get(metric_name, [])
        if not samples:
            # If no samples, pass with 0.0 metrics
            return BudgetMetricReport(
                metric_name=metric_name,
                sample_count=0,
                min_ms=0.0,
                max_ms=0.0,
                mean_ms=0.0,
                p50_ms=0.0,
                p90_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
                budget_limit_ms=limit_ms,
                passed=True,
                details="No samples recorded; default passed.",
            )

        sorted_samples = sorted(samples)
        sample_count = len(sorted_samples)
        min_ms = sorted_samples[0]
        max_ms = sorted_samples[-1]
        mean_ms = statistics.fmean(sorted_samples)
        p50_ms = self._compute_percentile(sorted_samples, 50)
        p90_ms = self._compute_percentile(sorted_samples, 90)
        p95_ms = self._compute_percentile(sorted_samples, 95)
        p99_ms = self._compute_percentile(sorted_samples, 99)

        target_value = p95_ms if use_p95 else mean_ms
        passed = target_value <= limit_ms
        
        target_name = "P95" if use_p95 else "Mean"
        details = (
            f"{target_name}: {target_value:.4f}ms <= limit {limit_ms:.4f}ms -> "
            f"{'PASS' if passed else 'FAIL'}"
        )

        return BudgetMetricReport(
            metric_name=metric_name,
            sample_count=sample_count,
            min_ms=min_ms,
            max_ms=max_ms,
            mean_ms=mean_ms,
            p50_ms=p50_ms,
            p90_ms=p90_ms,
            p95_ms=p95_ms,
            p99_ms=p99_ms,
            budget_limit_ms=limit_ms,
            passed=passed,
            details=details,
        )

    def evaluate_all(self) -> PerformanceCertificationResult:
        """
        Evaluate all defined budgets and return the comprehensive certification result.
        """
        b = self._budgets
        reports: Dict[str, BudgetMetricReport] = {
            "event_publish": self.evaluate_metric("event_publish", b.max_event_publish_p95_ms, use_p95=True),
            "dispatcher_planning": self.evaluate_metric("dispatcher_planning", b.max_dispatcher_planning_p95_ms, use_p95=True),
            "consumer_planning": self.evaluate_metric("consumer_planning", b.max_consumer_planning_ms, use_p95=False),
            "worker_overhead": self.evaluate_metric("worker_overhead", b.max_worker_overhead_ms, use_p95=False),
            "trace_overhead": self.evaluate_metric("trace_overhead", b.max_trace_overhead_per_span_ms, use_p95=False),
            "scheduler_planning_10k": self.evaluate_metric("scheduler_planning_10k", b.max_scheduler_planning_10k_events_ms, use_p95=False),
        }

        violations = [
            f"{name} budget breached: {rep.details}"
            for name, rep in reports.items()
            if not rep.passed
        ]

        total_samples = sum(len(s) for s in self._samples.values())
        return PerformanceCertificationResult(
            passed=len(violations) == 0,
            total_samples=total_samples,
            reports=reports,
            violations=violations,
        )

    def enforce_certification(self) -> PerformanceCertificationResult:
        """
        Evaluate all budgets and raise an AssertionError if any budget is breached.
        """
        result = self.evaluate_all()
        if not result.passed:
            raise AssertionError(
                f"Performance Certification Failed with {len(result.violations)} budget violation(s):\n"
                + "\n".join(f" - {v}" for v in result.violations)
            )
        return result

    def reset(self) -> None:
        """Clear all collected samples."""
        for k in self._samples:
            self._samples[k].clear()


# Global budget tracker instance
budget_tracker = PerformanceBudgetTracker()
