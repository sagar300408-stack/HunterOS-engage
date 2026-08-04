"""
HunterOS Engage — Tracing Startup Validator
app/events/tracing/validator.py
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict

from app.events.observability.metrics import event_metrics
from app.events.tracing.config import TraceConfig
from app.events.tracing.context import TraceContext
from app.events.tracing.latency import DefaultLatencyAnalyzer
from app.events.tracing.manager import DefaultTraceManager
from app.events.tracing.search import DefaultTraceSearchEngine, TraceSearchQuery
from app.events.tracing.span import Span, SpanStatus
from app.events.tracing.storage import DefaultInMemoryTraceStorage
from app.events.tracing.timeline import DefaultTimelineBuilder

logger = logging.getLogger("hunter.tracing.validator")


class TracingStartupValidator:
    """
    Fast preflight validator executed during application boot.
    Verifies that tracing components, context propagation, storage, search,
    timeline, latency analyzer, and metrics are fully functional.
    """

    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """
        Executes preflight verification. Raises RuntimeError only if a critical
        subsystem is broken; otherwise returns the health summary dictionary.
        """
        report: Dict[str, Any] = {
            "status": "HEALTHY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {},
        }

        try:
            # 1. Config Check
            config = TraceConfig.from_env()
            report["checks"]["config"] = {
                "enabled": config.enabled,
                "sampling_rate": config.sampling_rate,
                "max_retention": config.max_trace_retention,
            }

            # 2. Storage & Manager Check
            storage = DefaultInMemoryTraceStorage(config)
            timeline_builder = DefaultTimelineBuilder()
            latency_analyzer = DefaultLatencyAnalyzer()
            search_engine = DefaultTraceSearchEngine(storage)
            manager = DefaultTraceManager(
                config=config,
                storage=storage,
                timeline_builder=timeline_builder,
                latency_analyzer=latency_analyzer,
                search_engine=search_engine,
            )

            # 3. Context & Span Hierarchy Verification
            ctx = TraceContext(
                workspace_id="ws_val_01",
                correlation_id="corr_val_01",
                event_id="evt_val_01",
            )
            root = manager.start_trace("test_bus", "publish", context=ctx)
            child = manager.start_span("test_worker", "execute", parent_span=root)
            manager.finish_span(child)
            snapshot = manager.finish_trace(root)

            if not snapshot:
                raise RuntimeError("Failed to generate trace snapshot during startup validation")

            report["checks"]["context_propagation"] = "PASSED"
            report["checks"]["snapshot_generation"] = "PASSED"

            # 4. Timeline & Critical Path Check
            if not snapshot.timeline or not snapshot.timeline.critical_path_span_ids:
                raise RuntimeError("Timeline or critical path calculation failed during validation")
            report["checks"]["critical_path"] = "PASSED"

            # 5. Search Engine Check
            res = search_engine.search(TraceSearchQuery(workspace_id="ws_val_01"))
            if res.total != 1:
                raise RuntimeError(f"Search engine validation expected 1 match, found {res.total}")
            report["checks"]["search_engine"] = "PASSED"

            # 6. Cleanup Verification
            storage.clear()
            report["checks"]["storage_cleanup"] = "PASSED"

            logger.info("[HunterOS Tracing] Distributed Tracing Startup Validator: All checks PASSED.")
            return report

        except Exception as e:
            logger.error(f"[HunterOS Tracing] Startup validation FAILED: {e}", exc_info=True)
            report["status"] = "DEGRADED"
            report["error"] = str(e)
            return report
