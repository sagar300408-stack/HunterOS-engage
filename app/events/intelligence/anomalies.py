"""
HunterOS Engage — Anomaly Detector
app/events/intelligence/anomalies.py

Statistical anomaly detection for execution durations, queue wait latencies,
and abnormal concurrency patterns across completed traces.
"""

from abc import ABC, abstractmethod
import math
from typing import List, Optional

from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.models import (
    AnomalyReport,
    SeverityLevel,
)
from app.events.tracing.snapshot import TraceSnapshot


class AbstractAnomalyDetector(ABC):
    """
    Interface for execution anomaly detectors.
    """

    @abstractmethod
    def detect_anomalies(self, snapshots: List[TraceSnapshot]) -> List[AnomalyReport]:
        """
        Analyzes a batch of completed trace snapshots and detects statistical outliers.
        """
        pass


class DefaultAnomalyDetector(AbstractAnomalyDetector):
    """
    Standard Z-score statistical anomaly detector.
    """

    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or IntelligenceConfig()

    def detect_anomalies(self, snapshots: List[TraceSnapshot]) -> List[AnomalyReport]:
        if len(snapshots) < 5:
            return []

        anomalies: List[AnomalyReport] = []
        durations = [s.root_span.duration_ms for s in snapshots if s.root_span and s.root_span.duration_ms is not None]
        if len(durations) < 5:
            return []

        mean_dur = sum(durations) / len(durations)
        variance = sum((d - mean_dur) ** 2 for d in durations) / len(durations)
        std_dev = math.sqrt(variance)

        if std_dev < 1.0:
            return []

        z_threshold = self.config.anomaly_z_score_threshold

        for s in snapshots:
            if not s.root_span or s.root_span.duration_ms is None:
                continue

            dur = s.root_span.duration_ms
            z_score = (dur - mean_dur) / std_dev

            if z_score >= z_threshold:
                severity = SeverityLevel.HIGH if z_score >= 3.5 else SeverityLevel.MEDIUM
                anomalies.append(
                    AnomalyReport(
                        trace_id=s.trace_id,
                        metric_name="trace_duration_ms",
                        observed_value=dur,
                        expected_value=mean_dur,
                        z_score=z_score,
                        severity=severity,
                        description=f"Trace duration {dur:.1f}ms is statistically anomalous (Z={z_score:.2f}, Mean={mean_dur:.1f}ms, σ={std_dev:.1f}ms).",
                    )
                )

        return anomalies
