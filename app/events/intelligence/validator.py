"""
HunterOS Engage — Execution Intelligence Startup Validator
app/events/intelligence/validator.py

Pre-flight validator for the Execution Intelligence engine, ensuring root cause
analyzers, bottleneck detectors, pattern classifiers, and health scoring are fully operational.
"""

from datetime import datetime, timezone
import uuid

from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.engine import DefaultExecutionIntelligenceEngine
from app.events.tracing.context import TraceContext
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import Span, SpanStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutionIntelligenceStartupValidator:
    """
    Validates the integrity of the Execution Intelligence subsystem during application startup.
    """

    @classmethod
    def validate(cls) -> bool:
        """
        Executes a self-contained pre-flight check of all intelligence modules.
        Returns True if all components initialize and pass verification.
        """
        logger.info("[Startup] Validating Execution Intelligence Engine...")
        try:
            config = IntelligenceConfig()
            engine = DefaultExecutionIntelligenceEngine(config=config)

            # Create mock completed trace with simulated failure and bottleneck
            trace_id = uuid.uuid4().hex
            ctx = TraceContext(trace_id=trace_id, event_id="evt_test", workspace_id="ws_test")
            root_span = Span(
                span_id=uuid.uuid4().hex,
                trace_id=trace_id,
                context=ctx,
                component="EventPipeline",
                operation="process_event",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_ms=250.0,
                status=SpanStatus.FAILED,
                error="Lock contention timeout",
            )
            child_span = Span(
                span_id=uuid.uuid4().hex,
                trace_id=trace_id,
                context=ctx,
                parent_span_id=root_span.span_id,
                component="EngagementScoreConsumer",
                operation="handle_event",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_ms=180.0,
                status=SpanStatus.SUCCESS,
            )

            snapshot = TraceSnapshot(
                trace_id=trace_id,
                root_span=root_span,
                spans=[root_span, child_span],
            )

            # Ingest completed snapshot
            engine.record_completed_trace(snapshot)

            # Verify analysis outputs
            report = engine.get_intelligence_report()
            assert report is not None, "Intelligence report should not be None"
            assert report.health.overall_score >= 0, "Health score must be non-negative"

            rcs = engine.get_root_causes()
            assert len(rcs) >= 1, "Should have detected root cause from failed span"

            bns = engine.get_bottlenecks()
            assert len(bns) >= 1, "Should have detected consumer bottleneck (>100ms)"

            trends = engine.get_historical_trends()
            assert trends.total_traces == 1, "Historical trends should reflect 1 analyzed trace"

            logger.info("[Startup] Execution Intelligence Engine validated successfully (Health Score: %d/100).", report.health.overall_score)
            return True

        except Exception as exc:
            logger.error("[Startup] Execution Intelligence Engine validation FAILED: %s", exc, exc_info=True)
            return False
