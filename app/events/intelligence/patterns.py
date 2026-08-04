"""
HunterOS Engage — Pattern Detector
app/events/intelligence/patterns.py

Identifies recurring cross-trace patterns: repeated failures, recurring slow consumers,
partition hotspots, worker skew, and retry storms across completed traces.
"""

from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.models import (
    PatternReport,
    PatternType,
    SeverityLevel,
)
from app.events.tracing.snapshot import TraceSnapshot
from app.events.tracing.span import SpanStatus


class AbstractPatternDetector(ABC):
    """
    Interface for cross-trace pattern detectors.
    """

    @abstractmethod
    def detect_patterns(self, snapshots: List[TraceSnapshot]) -> List[PatternReport]:
        """
        Analyzes a batch or rolling window of completed traces and returns detected patterns.
        """
        pass


class DefaultPatternDetector(AbstractPatternDetector):
    """
    Standard production pattern detector.
    Aggregates statistics across completed traces to identify skew, storms, and recurring hotspots.
    """

    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or IntelligenceConfig()

    def detect_patterns(self, snapshots: List[TraceSnapshot]) -> List[PatternReport]:
        if not snapshots:
            return []

        patterns: List[PatternReport] = []
        total_traces = len(snapshots)

        failure_counts_by_event: Counter = Counter()
        failure_counts_by_consumer: Counter = Counter()
        slow_consumer_counts: Counter = Counter()
        partition_counts: Counter = Counter()
        worker_counts: Counter = Counter()
        dispatcher_counts: Counter = Counter()
        retry_count = 0
        dead_letter_count = 0

        earliest_time = datetime.now(timezone.utc)
        latest_time = datetime.fromtimestamp(0, timezone.utc)

        for s in snapshots:
            root = s.root_span
            if not root:
                continue

            if root.start_time:
                if root.start_time < earliest_time:
                    earliest_time = root.start_time
                if root.start_time > latest_time:
                    latest_time = root.start_time

            ctx = root.context
            if ctx:
                if ctx.partition_key:
                    partition_counts[ctx.partition_key] += 1
                if ctx.worker_id:
                    worker_counts[ctx.worker_id] += 1
                if ctx.dispatcher_id:
                    dispatcher_counts[ctx.dispatcher_id] += 1

            if root.status == SpanStatus.FAILED:
                evt_name = (ctx.to_dict().get("event_name") if ctx else None) or root.operation
                failure_counts_by_event[evt_name] += 1

            if s.retry_history:
                retry_count += len(s.retry_history)

            # Check individual spans
            for span in s.spans:
                comp = span.component
                op = span.operation
                dur = span.duration_ms or 0.0

                if span.status == SpanStatus.FAILED and "consumer" in comp.lower():
                    failure_counts_by_consumer[comp] += 1

                if ("consumer" in comp.lower() or "handle_event" in op.lower()) and dur >= self.config.slow_consumer_threshold_ms:
                    slow_consumer_counts[comp] += 1

                if "dead_letter" in span.metadata or span.status == SpanStatus.FAILED:
                    if "dead_letter" in str(span.error).lower():
                        dead_letter_count += 1

        # 1. Repeated Failures by Event Type / Consumer
        for evt, count in failure_counts_by_event.items():
            if count >= self.config.repeated_failure_threshold:
                patterns.append(
                    PatternReport(
                        pattern_type=PatternType.REPEATED_FAILURE,
                        description=f"Event '{evt}' failed repeatedly ({count} times across {total_traces} traces).",
                        occurrences=count,
                        affected_entities=[str(evt)],
                        severity=SeverityLevel.HIGH if count >= 5 else SeverityLevel.MEDIUM,
                        first_seen=earliest_time,
                        last_seen=latest_time,
                        evidence={"failure_count": count, "sample_size": total_traces},
                    )
                )

        for consumer, count in failure_counts_by_consumer.items():
            if count >= self.config.repeated_failure_threshold:
                patterns.append(
                    PatternReport(
                        pattern_type=PatternType.REPEATED_FAILURE,
                        description=f"Consumer '{consumer}' failed repeatedly ({count} times).",
                        occurrences=count,
                        affected_entities=[consumer],
                        severity=SeverityLevel.HIGH,
                        first_seen=earliest_time,
                        last_seen=latest_time,
                        evidence={"consumer_failures": count},
                    )
                )

        # 2. Recurring Slow Consumers
        for consumer, count in slow_consumer_counts.items():
            if count >= self.config.recurring_slow_consumer_threshold:
                patterns.append(
                    PatternReport(
                        pattern_type=PatternType.RECURRING_SLOW_CONSUMER,
                        description=f"Consumer '{consumer}' exceeded {self.config.slow_consumer_threshold_ms:.0f}ms in {count} traces.",
                        occurrences=count,
                        affected_entities=[consumer],
                        severity=SeverityLevel.MEDIUM,
                        first_seen=earliest_time,
                        last_seen=latest_time,
                        evidence={"slow_invocations": count},
                    )
                )

        # 3. Partition Hotspots
        if total_traces >= 5 and partition_counts:
            for p_key, count in partition_counts.items():
                ratio = count / total_traces
                if ratio >= self.config.partition_hotspot_ratio:
                    patterns.append(
                        PatternReport(
                            pattern_type=PatternType.PARTITION_HOTSPOT,
                            description=f"Partition '{p_key}' is a hotspot handling {count}/{total_traces} ({ratio * 100:.1f}%) of traffic.",
                            occurrences=count,
                            affected_entities=[str(p_key)],
                            severity=SeverityLevel.HIGH if ratio >= 0.6 else SeverityLevel.MEDIUM,
                            first_seen=earliest_time,
                            last_seen=latest_time,
                            evidence={"ratio": round(ratio, 3), "partition_key": p_key},
                        )
                    )

        # 4. Worker Hotspots
        if total_traces >= 5 and worker_counts:
            for w_id, count in worker_counts.items():
                ratio = count / total_traces
                if ratio >= self.config.worker_hotspot_ratio:
                    patterns.append(
                        PatternReport(
                            pattern_type=PatternType.WORKER_HOTSPOT,
                            description=f"Worker '{w_id}' processed {count}/{total_traces} ({ratio * 100:.1f}%) of traces (worker skew).",
                            occurrences=count,
                            affected_entities=[str(w_id)],
                            severity=SeverityLevel.MEDIUM,
                            first_seen=earliest_time,
                            last_seen=latest_time,
                            evidence={"ratio": round(ratio, 3), "worker_id": w_id},
                        )
                    )

        # 5. Retry Storms
        if retry_count >= self.config.retry_storm_threshold:
            patterns.append(
                PatternReport(
                    pattern_type=PatternType.RETRY_STORM,
                    description=f"Retry storm detected with {retry_count} total retries across {total_traces} traces.",
                    occurrences=retry_count,
                    affected_entities=["retry_engine"],
                    severity=SeverityLevel.CRITICAL if retry_count >= 10 else SeverityLevel.HIGH,
                    first_seen=earliest_time,
                    last_seen=latest_time,
                    evidence={"total_retries": retry_count, "sample_size": total_traces},
                )
            )

        return patterns
