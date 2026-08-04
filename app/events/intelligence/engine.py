"""
HunterOS Engage — Central Execution Intelligence Engine
app/events/intelligence/engine.py

Central orchestrator for distributed execution analytics, root cause isolation,
bottleneck detection, recurring patterns, and multi-dimensional health scoring.
"""

from abc import ABC, abstractmethod
from collections import deque
import threading
from typing import Deque, Dict, List, Optional

from app.events.intelligence.analysis import HistoricalAnalyticsEngine, HistoricalTrends
from app.events.intelligence.anomalies import AbstractAnomalyDetector, DefaultAnomalyDetector
from app.events.intelligence.bottlenecks import AbstractBottleneckAnalyzer, DefaultBottleneckAnalyzer
from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.health import AbstractHealthCalculator, DefaultHealthCalculator
from app.events.intelligence.models import (
    AnomalyReport,
    BottleneckReport,
    ExecutionIntelligenceReport,
    PatternReport,
    PatternType,
    Recommendation,
    RootCauseReport,
    SystemHealthReport,
)
from app.events.intelligence.patterns import AbstractPatternDetector, DefaultPatternDetector
from app.events.intelligence.recommendations import AbstractRecommendationEngine, DefaultRecommendationEngine
from app.events.intelligence.root_cause import AbstractRootCauseAnalyzer, DefaultRootCauseAnalyzer
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import SpanStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AbstractExecutionIntelligenceEngine(ABC):
    """
    Interface for execution intelligence engines.
    """

    @abstractmethod
    def record_completed_trace(self, snapshot: TraceSnapshot) -> None:
        """
        Ingests a completed trace snapshot into the intelligence engine.
        Must NEVER analyze active/running traces.
        """
        pass

    @abstractmethod
    def get_intelligence_report(self) -> ExecutionIntelligenceReport:
        """
        Generates and returns the latest unified execution intelligence report.
        """
        pass

    @abstractmethod
    def get_root_causes(self, limit: int = 50) -> List[RootCauseReport]:
        """
        Returns recent root cause failure analyses.
        """
        pass

    @abstractmethod
    def get_bottlenecks(self, limit: int = 50) -> List[BottleneckReport]:
        """
        Returns recent execution bottlenecks.
        """
        pass

    @abstractmethod
    def get_patterns(self) -> List[PatternReport]:
        """
        Returns detected recurring patterns and hotspots.
        """
        pass

    @abstractmethod
    def get_recommendations(self, limit: int = 50) -> List[Recommendation]:
        """
        Returns actionable operational recommendations.
        """
        pass

    @abstractmethod
    def get_health_report(self) -> SystemHealthReport:
        """
        Returns the multi-dimensional platform health score.
        """
        pass

    @abstractmethod
    def get_historical_trends(self) -> HistoricalTrends:
        """
        Returns rolling statistical percentiles and throughput trends.
        """
        pass


class DefaultExecutionIntelligenceEngine(AbstractExecutionIntelligenceEngine):
    """
    Thread-safe, failure-isolated production Execution Intelligence Engine.
    Consumes completed TraceSnapshots only.
    """

    def __init__(
        self,
        config: Optional[IntelligenceConfig] = None,
        root_cause_analyzer: Optional[AbstractRootCauseAnalyzer] = None,
        bottleneck_analyzer: Optional[AbstractBottleneckAnalyzer] = None,
        pattern_detector: Optional[AbstractPatternDetector] = None,
        anomaly_detector: Optional[AbstractAnomalyDetector] = None,
        recommendation_engine: Optional[AbstractRecommendationEngine] = None,
        health_calculator: Optional[AbstractHealthCalculator] = None,
    ):
        self.config = config or IntelligenceConfig.from_env()
        self.root_cause_analyzer = root_cause_analyzer or DefaultRootCauseAnalyzer(self.config)
        self.bottleneck_analyzer = bottleneck_analyzer or DefaultBottleneckAnalyzer(self.config)
        self.pattern_detector = pattern_detector or DefaultPatternDetector(self.config)
        self.anomaly_detector = anomaly_detector or DefaultAnomalyDetector(self.config)
        self.recommendation_engine = recommendation_engine or DefaultRecommendationEngine(self.config)
        self.health_calculator = health_calculator or DefaultHealthCalculator(self.config)

        self._lock = threading.Lock()
        self._history: Deque[TraceSnapshot] = deque(maxlen=self.config.historical_window_size)
        self._root_causes: Deque[RootCauseReport] = deque(maxlen=self.config.max_stored_root_causes)
        self._bottlenecks: Deque[BottleneckReport] = deque(maxlen=self.config.max_stored_bottlenecks)

    def record_completed_trace(self, snapshot: TraceSnapshot) -> None:
        """
        Ingests a completed trace snapshot.
        Safely ignores active/running traces to ensure zero contention with live execution.
        """
        if not self.config.enabled or not snapshot or not snapshot.root_span:
            return

        # Explicit invariant: MUST be completed, NEVER running
        if snapshot.root_span.status == SpanStatus.RUNNING:
            return

        try:
            with self._lock:
                self._history.append(snapshot)

            # Analyze individual trace root causes & bottlenecks
            rc = self.root_cause_analyzer.analyze_root_cause(snapshot)
            bns = self.bottleneck_analyzer.analyze_bottlenecks(snapshot)

            with self._lock:
                if rc:
                    self._root_causes.append(rc)
                if bns:
                    self._bottlenecks.extend(bns)

            # Passively update observability metrics
            self._update_metrics_safely(rc, bns)

        except Exception as exc:
            # Observability passivity invariant: never let intelligence exceptions propagate
            logger.warning("Execution Intelligence trace analysis encountered error: %s", exc)

    def get_intelligence_report(self) -> ExecutionIntelligenceReport:
        try:
            with self._lock:
                snapshots = list(self._history)
                root_causes = list(self._root_causes)
                bottlenecks = list(self._bottlenecks)

            patterns = self.pattern_detector.detect_patterns(snapshots)
            anomalies = self.anomaly_detector.detect_anomalies(snapshots)
            recommendations = self.recommendation_engine.generate_recommendations(
                root_causes=root_causes,
                bottlenecks=bottlenecks,
                patterns=patterns,
            )
            health = self.health_calculator.calculate_health(
                snapshots=snapshots,
                root_causes=root_causes,
                bottlenecks=bottlenecks,
                patterns=patterns,
            )

            return ExecutionIntelligenceReport(
                health=health,
                root_causes=root_causes,
                bottlenecks=bottlenecks,
                patterns=patterns,
                anomalies=anomalies,
                recommendations=recommendations,
                total_traces_analyzed=len(snapshots),
            )
        except Exception as exc:
            logger.warning("Failed to generate Execution Intelligence report: %s", exc)
            return ExecutionIntelligenceReport(
                health=self.health_calculator.calculate_health([], [], [], []),
                total_traces_analyzed=0,
            )

    def get_root_causes(self, limit: int = 50) -> List[RootCauseReport]:
        with self._lock:
            items = list(self._root_causes)
        return items[-limit:]

    def get_bottlenecks(self, limit: int = 50) -> List[BottleneckReport]:
        with self._lock:
            items = list(self._bottlenecks)
        return items[-limit:]

    def get_patterns(self) -> List[PatternReport]:
        with self._lock:
            snapshots = list(self._history)
        return self.pattern_detector.detect_patterns(snapshots)

    def get_recommendations(self, limit: int = 50) -> List[Recommendation]:
        report = self.get_intelligence_report()
        return report.recommendations[:limit]

    def get_health_report(self) -> SystemHealthReport:
        with self._lock:
            snapshots = list(self._history)
            root_causes = list(self._root_causes)
            bottlenecks = list(self._bottlenecks)
        patterns = self.pattern_detector.detect_patterns(snapshots)
        return self.health_calculator.calculate_health(
            snapshots=snapshots,
            root_causes=root_causes,
            bottlenecks=bottlenecks,
            patterns=patterns,
        )

    def get_historical_trends(self) -> HistoricalTrends:
        with self._lock:
            snapshots = list(self._history)
        return HistoricalAnalyticsEngine.calculate_trends(snapshots)

    def _update_metrics_safely(self, rc: Optional[RootCauseReport], bns: List[BottleneckReport]) -> None:
        """
        Updates EventMetrics counters in a thread-safe, non-disruptive manner.
        """
        try:
            from app.events.observability.metrics import event_metrics

            if rc:
                event_metrics.record_root_cause()
            if bns:
                event_metrics.record_bottlenecks(len(bns))
        except Exception:
            pass
