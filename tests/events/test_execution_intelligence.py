"""
HunterOS Engage — Execution Intelligence & Root Cause Analysis Test Suite
tests/events/test_execution_intelligence.py

Comprehensive test suite verifying:
- Root cause failure isolation & propagation chains
- Bottleneck detection across consumers, queues, dispatchers, and database
- Cross-trace pattern detection (repeated failures, recurring slow consumers, partition skew, retry storms)
- Statistical anomaly detection (Z-score outliers)
- Actionable operational recommendation generation
- Multi-dimensional subsystem health scoring (0-100)
- Historical analytics and latency percentiles (P50, P90, P95, P99)
- Completed-traces-only ingestion invariant
- Failure isolation & passive non-disruption guarantees
- Startup pre-flight validation
"""

from datetime import datetime, timezone
import pytest
import uuid

from app.events.intelligence.analysis import HistoricalAnalyticsEngine
from app.events.intelligence.anomalies import DefaultAnomalyDetector
from app.events.intelligence.bottlenecks import DefaultBottleneckAnalyzer
from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.engine import DefaultExecutionIntelligenceEngine
from app.events.intelligence.health import DefaultHealthCalculator
from app.events.intelligence.models import (
    BottleneckCategory,
    FailureCategory,
    HealthComponent,
    PatternType,
    SeverityLevel,
)
from app.events.intelligence.patterns import DefaultPatternDetector
from app.events.intelligence.recommendations import DefaultRecommendationEngine
from app.events.intelligence.root_cause import DefaultRootCauseAnalyzer
from app.events.intelligence.validator import ExecutionIntelligenceStartupValidator
from app.events.observability.metrics import event_metrics
from app.events.tracing.context import TraceContext
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import Span, SpanStatus


def _create_mock_snapshot(
    trace_id: str,
    duration_ms: float = 50.0,
    status: SpanStatus = SpanStatus.SUCCESS,
    error: str = None,
    partition_key: str = "org_1",
    worker_id: str = "worker_1",
    dispatcher_id: str = "disp_1",
    spans: list = None,
    retry_history: list = None,
    replay_history: list = None,
) -> TraceSnapshot:
    ctx = TraceContext(
        trace_id=trace_id,
        event_id=f"evt_{trace_id[:8]}",
        workspace_id="ws_default",
        partition_key=partition_key,
        worker_id=worker_id,
        dispatcher_id=dispatcher_id,
    )
    root = Span(
        span_id=uuid.uuid4().hex,
        trace_id=trace_id,
        context=ctx,
        component="EventPipeline",
        operation="process_event",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        duration_ms=duration_ms,
        status=status,
        error=error,
    )
    all_spans = [root] + (spans or [])
    return TraceSnapshot(
        trace_id=trace_id,
        root_span=root,
        spans=all_spans,
        retry_history=retry_history or [],
        replay_history=replay_history or [],
    )


class TestExecutionIntelligence:
    """Test suite for the Execution Intelligence Platform."""

    def test_root_cause_consumer_exception(self):
        """Scenario 1: Detects consumer exception as root cause."""
        analyzer = DefaultRootCauseAnalyzer()
        trace_id = uuid.uuid4().hex
        ctx = TraceContext(trace_id=trace_id)

        root = Span(
            span_id=uuid.uuid4().hex,
            trace_id=trace_id,
            context=ctx,
            component="EventPipeline",
            operation="process",
            duration_ms=80.0,
            status=SpanStatus.FAILED,
            error="Consumer execution failed",
        )
        child = Span(
            span_id=uuid.uuid4().hex,
            trace_id=trace_id,
            context=ctx,
            parent_span_id=root.span_id,
            component="EngagementScoreConsumer",
            operation="handle_event",
            duration_ms=45.0,
            status=SpanStatus.FAILED,
            error="ZeroDivisionError: integer division by zero",
        )
        snapshot = TraceSnapshot(trace_id=trace_id, root_span=root, spans=[root, child])

        report = analyzer.analyze_root_cause(snapshot)
        assert report is not None
        assert report.category == FailureCategory.CONSUMER_EXCEPTION
        assert report.originating_component == "EngagementScoreConsumer"
        assert "ZeroDivisionError" in report.error_message
        assert report.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)

    def test_root_cause_lock_contention(self):
        """Scenario 2: Detects partition lock contention."""
        analyzer = DefaultRootCauseAnalyzer()
        trace_id = uuid.uuid4().hex
        ctx = TraceContext(trace_id=trace_id)

        root = Span(
            span_id=uuid.uuid4().hex,
            trace_id=trace_id,
            context=ctx,
            component="PartitionScheduler",
            operation="acquire_lock",
            duration_ms=120.0,
            status=SpanStatus.FAILED,
            error="PartitionLockContention: lock held by another worker",
        )
        snapshot = TraceSnapshot(trace_id=trace_id, root_span=root, spans=[root])

        report = analyzer.analyze_root_cause(snapshot)
        assert report is not None
        assert report.category == FailureCategory.LOCK_CONTENTION
        assert "PartitionLockContention" in report.error_message

    def test_multi_stage_failure_propagation(self):
        """Scenario 3: Maps multi-stage failure propagation chain."""
        analyzer = DefaultRootCauseAnalyzer()
        trace_id = uuid.uuid4().hex
        ctx = TraceContext(trace_id=trace_id)

        root = Span(
            span_id="s1",
            trace_id=trace_id,
            context=ctx,
            component="EventPipeline",
            operation="dispatch",
            start_time=datetime.fromtimestamp(100, timezone.utc),
            duration_ms=150.0,
            status=SpanStatus.FAILED,
            error="Cascaded dispatch failure",
        )
        span_db = Span(
            span_id="s2",
            trace_id=trace_id,
            context=ctx,
            parent_span_id="s1",
            component="EventStore",
            operation="persist",
            start_time=datetime.fromtimestamp(101, timezone.utc),
            duration_ms=60.0,
            status=SpanStatus.FAILED,
            error="PostgreSQL unique constraint violation",
        )
        span_cons = Span(
            span_id="s3",
            trace_id=trace_id,
            context=ctx,
            parent_span_id="s1",
            component="LeadConsumer",
            operation="handle",
            start_time=datetime.fromtimestamp(102, timezone.utc),
            duration_ms=10.0,
            status=SpanStatus.FAILED,
            error="Event not persisted in store",
        )
        snapshot = TraceSnapshot(trace_id=trace_id, root_span=root, spans=[root, span_db, span_cons])

        report = analyzer.analyze_root_cause(snapshot)
        assert report is not None
        assert report.originating_component == "EventStore"
        assert report.category == FailureCategory.DATABASE_ERROR
        assert len(report.failure_chain) == 3
        assert "LeadConsumer" in report.downstream_impacted_components

    def test_retry_and_replay_root_causes(self):
        """Scenario 4: Detects retry and replay failures."""
        analyzer = DefaultRootCauseAnalyzer()
        trace_id = uuid.uuid4().hex
        ctx = TraceContext(trace_id=trace_id)

        root = Span(
            span_id="s_retry",
            trace_id=trace_id,
            context=ctx,
            component="RetryEngine",
            operation="retry_event",
            metadata={"retry_delay_seconds": 5},
            duration_ms=100.0,
            status=SpanStatus.FAILED,
            error="Connection timeout during retry attempt",
        )
        snapshot = TraceSnapshot(
            trace_id=trace_id,
            root_span=root,
            spans=[root],
            retry_history=[{"attempt": 1, "reason": "timeout"}],
        )

        report = analyzer.analyze_root_cause(snapshot)
        assert report is not None
        assert report.is_retry_failure is True
        assert report.category == FailureCategory.TIMEOUT

    def test_consumer_bottleneck_detection(self):
        """Scenario 5: Detects slow consumer bottleneck exceeding threshold."""
        config = IntelligenceConfig(slow_consumer_threshold_ms=100.0)
        analyzer = DefaultBottleneckAnalyzer(config)
        trace_id = uuid.uuid4().hex
        ctx = TraceContext(trace_id=trace_id)

        root = Span(span_id="r1", trace_id=trace_id, context=ctx, component="Pipeline", operation="run", duration_ms=250.0)
        consumer_span = Span(
            span_id="c1",
            trace_id=trace_id,
            context=ctx,
            parent_span_id="r1",
            component="ReportGenerationConsumer",
            operation="handle_event",
            duration_ms=180.0,
        )
        snapshot = TraceSnapshot(trace_id=trace_id, root_span=root, spans=[root, consumer_span])

        bottlenecks = analyzer.analyze_bottlenecks(snapshot)
        assert len(bottlenecks) >= 1
        b = bottlenecks[0]
        assert b.category == BottleneckCategory.SLOW_CONSUMER
        assert b.component == "ReportGenerationConsumer"
        assert b.duration_ms == 180.0
        assert b.percentage_of_trace >= 70.0

    def test_queue_congestion_bottleneck(self):
        """Scenario 6: Detects broker queue wait bottleneck."""
        config = IntelligenceConfig(slow_queue_threshold_ms=150.0)
        analyzer = DefaultBottleneckAnalyzer(config)
        trace_id = uuid.uuid4().hex
        ctx = TraceContext(trace_id=trace_id)

        root = Span(span_id="r1", trace_id=trace_id, context=ctx, component="Pipeline", operation="run", duration_ms=300.0)
        queue_span = Span(
            span_id="q1",
            trace_id=trace_id,
            context=ctx,
            parent_span_id="r1",
            component="CeleryQueue",
            operation="queue_wait",
            duration_ms=210.0,
        )
        snapshot = TraceSnapshot(trace_id=trace_id, root_span=root, spans=[root, queue_span])

        bottlenecks = analyzer.analyze_bottlenecks(snapshot)
        assert len(bottlenecks) >= 1
        b = bottlenecks[0]
        assert b.category == BottleneckCategory.QUEUE_CONGESTION
        assert b.duration_ms == 210.0

    def test_worker_and_database_bottlenecks(self):
        """Scenario 7: Detects worker saturation and database latency."""
        config = IntelligenceConfig(slow_worker_threshold_ms=200.0, slow_database_threshold_ms=50.0)
        analyzer = DefaultBottleneckAnalyzer(config)
        trace_id = uuid.uuid4().hex
        ctx = TraceContext(trace_id=trace_id)

        root = Span(span_id="r1", trace_id=trace_id, context=ctx, component="Pipeline", operation="run", duration_ms=500.0)
        db_span = Span(span_id="db1", trace_id=trace_id, context=ctx, component="event_store", operation="persist", duration_ms=90.0)
        worker_span = Span(span_id="w1", trace_id=trace_id, context=ctx, component="worker", operation="execute", duration_ms=250.0)
        snapshot = TraceSnapshot(trace_id=trace_id, root_span=root, spans=[root, db_span, worker_span])

        bottlenecks = analyzer.analyze_bottlenecks(snapshot)
        categories = {b.category for b in bottlenecks}
        assert BottleneckCategory.DATABASE_LATENCY in categories
        assert BottleneckCategory.WORKER_SATURATION in categories

    def test_repeated_failure_pattern_detection(self):
        """Scenario 8: Identifies repeated failures on the same consumer."""
        config = IntelligenceConfig(repeated_failure_threshold=3)
        detector = DefaultPatternDetector(config)

        snapshots = []
        for _ in range(4):
            t_id = uuid.uuid4().hex
            ctx = TraceContext(trace_id=t_id)
            root = Span(span_id=uuid.uuid4().hex, trace_id=t_id, context=ctx, component="Pipeline", operation="process", duration_ms=50.0, status=SpanStatus.FAILED)
            c_span = Span(span_id=uuid.uuid4().hex, trace_id=t_id, context=ctx, component="WebhookNotifierConsumer", operation="send", duration_ms=40.0, status=SpanStatus.FAILED, error="ConnectionRefusedError")
            snapshots.append(TraceSnapshot(trace_id=t_id, root_span=root, spans=[root, c_span]))

        patterns = detector.detect_patterns(snapshots)
        assert len(patterns) >= 1
        p = [p for p in patterns if p.pattern_type == PatternType.REPEATED_FAILURE][0]
        assert "WebhookNotifierConsumer" in p.affected_entities or "process" in p.affected_entities
        assert p.occurrences >= 3

    def test_recurring_slow_consumer_pattern(self):
        """Scenario 9: Identifies recurring slow consumers."""
        config = IntelligenceConfig(slow_consumer_threshold_ms=100.0, recurring_slow_consumer_threshold=3)
        detector = DefaultPatternDetector(config)

        snapshots = []
        for _ in range(4):
            t_id = uuid.uuid4().hex
            ctx = TraceContext(trace_id=t_id)
            root = Span(span_id=uuid.uuid4().hex, trace_id=t_id, context=ctx, component="Pipeline", operation="process", duration_ms=150.0)
            c_span = Span(span_id=uuid.uuid4().hex, trace_id=t_id, context=ctx, component="AIEvaluationConsumer", operation="handle_event", duration_ms=130.0)
            snapshots.append(TraceSnapshot(trace_id=t_id, root_span=root, spans=[root, c_span]))

        patterns = detector.detect_patterns(snapshots)
        slow_patterns = [p for p in patterns if p.pattern_type == PatternType.RECURRING_SLOW_CONSUMER]
        assert len(slow_patterns) >= 1
        assert "AIEvaluationConsumer" in slow_patterns[0].affected_entities

    def test_partition_hotspot_pattern(self):
        """Scenario 10: Identifies partition hotspot skew."""
        config = IntelligenceConfig(partition_hotspot_ratio=0.50)
        detector = DefaultPatternDetector(config)

        snapshots = []
        # 8 traces on partition 'org_alpha', 2 on 'org_beta'
        for i in range(10):
            p_key = "org_alpha" if i < 8 else "org_beta"
            snapshots.append(_create_mock_snapshot(uuid.uuid4().hex, partition_key=p_key))

        patterns = detector.detect_patterns(snapshots)
        hotspot_patterns = [p for p in patterns if p.pattern_type == PatternType.PARTITION_HOTSPOT]
        assert len(hotspot_patterns) >= 1
        assert "org_alpha" in hotspot_patterns[0].affected_entities
        assert hotspot_patterns[0].occurrences == 8

    def test_retry_storm_pattern(self):
        """Scenario 11: Identifies retry storm across traces."""
        config = IntelligenceConfig(retry_storm_threshold=5)
        detector = DefaultPatternDetector(config)

        snapshots = []
        for _ in range(3):
            snapshots.append(_create_mock_snapshot(uuid.uuid4().hex, retry_history=[{"attempt": 1}, {"attempt": 2}]))

        patterns = detector.detect_patterns(snapshots)
        retry_patterns = [p for p in patterns if p.pattern_type == PatternType.RETRY_STORM]
        assert len(retry_patterns) >= 1
        assert retry_patterns[0].occurrences == 6  # 3 * 2

    def test_statistical_anomaly_detection(self):
        """Scenario 12: Detects duration outlier using Z-score."""
        config = IntelligenceConfig(anomaly_z_score_threshold=2.0)
        detector = DefaultAnomalyDetector(config)

        snapshots = []
        # 10 baseline fast traces ~50ms
        for _ in range(10):
            snapshots.append(_create_mock_snapshot(uuid.uuid4().hex, duration_ms=50.0))
        # 1 massive spike trace 1500ms
        spike_id = uuid.uuid4().hex
        snapshots.append(_create_mock_snapshot(spike_id, duration_ms=1500.0))

        anomalies = detector.detect_anomalies(snapshots)
        assert len(anomalies) >= 1
        assert anomalies[0].trace_id == spike_id
        assert anomalies[0].z_score >= 2.0

    def test_recommendation_generation(self):
        """Scenario 13: Generates prioritized actionable recommendations."""
        engine = DefaultRecommendationEngine()
        root_causes = []
        t_id = uuid.uuid4().hex
        bottlenecks = [
            DefaultBottleneckAnalyzer().analyze_bottlenecks(
                _create_mock_snapshot(
                    t_id,
                    duration_ms=300.0,
                    spans=[
                        Span(
                            span_id="b1",
                            trace_id=t_id,
                            context=TraceContext(t_id),
                            component="HeavyNLPReportConsumer",
                            operation="handle_event",
                            duration_ms=250.0,
                        )
                    ],
                )
            )[0]
        ]
        patterns = [
            DefaultPatternDetector().detect_patterns(
                [_create_mock_snapshot(uuid.uuid4().hex, retry_history=[{"attempt": 1}] * 6)]
            )[0]
        ]

        recs = engine.generate_recommendations(root_causes, bottlenecks, patterns)
        assert len(recs) >= 2
        actions = {r.action_type for r in recs}
        assert "OPTIMIZE_CONSUMER" in actions
        assert "CONFIGURE_BACKOFF" in actions

    def test_health_score_calculation(self):
        """Scenario 14: Calculates multi-dimensional health scores (0-100)."""
        calculator = DefaultHealthCalculator()

        # Healthy baseline
        healthy_snapshots = [_create_mock_snapshot(uuid.uuid4().hex, duration_ms=40.0) for _ in range(5)]
        h_report = calculator.calculate_health(healthy_snapshots, [], [], [])
        assert h_report.overall_score >= 90
        assert h_report.status == "HEALTHY"

        # Degraded system with failures
        failed_snapshots = [_create_mock_snapshot(uuid.uuid4().hex, duration_ms=300.0, status=SpanStatus.FAILED) for _ in range(5)]
        d_report = calculator.calculate_health(failed_snapshots, [], [], [])
        assert d_report.overall_score < 60
        assert d_report.status in ("DEGRADED", "CRITICAL")
        assert d_report.subsystem_health[HealthComponent.FAILURE.value].score == 0

    def test_historical_trends_and_percentiles(self):
        """Scenario 15: Computes P50, P90, P95, P99 and throughput distributions."""
        snapshots = []
        for i in range(100):
            snapshots.append(_create_mock_snapshot(uuid.uuid4().hex, duration_ms=float(i + 1), partition_key=f"part_{i % 5}"))

        trends = HistoricalAnalyticsEngine.calculate_trends(snapshots)
        assert trends.total_traces == 100
        assert trends.completed_traces == 100
        assert trends.failed_traces == 0
        assert trends.failure_rate == 0.0
        assert round(trends.p50_duration_ms, 0) in (50.0, 51.0)
        assert round(trends.p95_duration_ms, 0) in (95.0, 96.0)
        assert round(trends.p99_duration_ms, 0) in (99.0, 100.0)
        assert len(trends.partition_distribution) == 5

    def test_completed_traces_only_invariant(self):
        """Scenario 16: Verifies running traces are NEVER analyzed to prevent contention."""
        engine = DefaultExecutionIntelligenceEngine()
        running_trace_id = uuid.uuid4().hex

        ctx = TraceContext(trace_id=running_trace_id)
        running_root = Span(
            span_id="r_run",
            trace_id=running_trace_id,
            context=ctx,
            component="LiveWorker",
            operation="live_execute",
            status=SpanStatus.RUNNING,
        )
        running_snapshot = TraceSnapshot(trace_id=running_trace_id, root_span=running_root, spans=[running_root])

        # Attempt to record running trace
        engine.record_completed_trace(running_snapshot)

        # Engine must ignore it
        assert len(engine.get_root_causes()) == 0
        assert len(engine.get_bottlenecks()) == 0
        assert engine.get_historical_trends().total_traces == 0

    def test_failure_isolation_passivity(self):
        """Scenario 17: Engine guarantees 100% failure isolation."""
        engine = DefaultExecutionIntelligenceEngine()
        # Ingesting None or corrupt objects must never raise exceptions
        engine.record_completed_trace(None)
        report = engine.get_intelligence_report()
        assert report is not None
        assert report.health.overall_score == 100

    def test_startup_validator(self):
        """Scenario 18: Startup validator completes successfully."""
        result = ExecutionIntelligenceStartupValidator.validate()
        assert result is True
