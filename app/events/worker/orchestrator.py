"""
HunterOS Engage — Consumer Orchestration Engine
app/events/worker/orchestrator.py

Declarative execution layer that runs multiple consumers for a single event
according to their ExecutionPolicy and — when an ExecutionPlan is provided —
their topologically-sorted dependency stages.

Two entry points
────────────────
    run(event, consumers, event_id)
        Flat execution (no dependency graph).  All consumers are bucketed
        by ExecutionPolicy and run in Phase 1/2/3 order.  Used when no
        consumer declares depends_on() or as a fallback.

    run_plan(event, plan, event_id)
        Stage-aware execution.  Stages are taken from ExecutionPlan (built
        by PlanBuilder).  Within each stage the same Phase 1/2/3 bucketing
        applies.  Stages execute sequentially; BACKGROUND consumers in every
        stage always run regardless of upstream failures.

Failure isolation
─────────────────
• ORDERED/CRITICAL  — serial; CRITICAL halts the ordered chain on failure
                      but cannot affect PARALLEL or BACKGROUND.
• PARALLEL          — asyncio.gather(return_exceptions=True); sibling-safe.
• BACKGROUND        — always runs; fire-and-monitor side-effects.
• Stage halt        — if a CRITICAL consumer fails in stage N, stages N+1…
                      are skipped (BACKGROUND consumers in those stages
                      still run because they are unconditional side-effects).

Every consumer is timed individually (wall-clock milliseconds).
Structured logs fire for consumer start, success, failure, and
stage/report summaries.
"""

from __future__ import annotations

import asyncio
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Sequence
from uuid import UUID

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.base_event import UniversalBaseEvent
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.events.worker.planner import ExecutionPlan

logger = get_logger(__name__)


# ── Result primitives ─────────────────────────────────────────────────────────

class ConsumerStatus(str, Enum):
    """Outcome of a single consumer execution attempt."""
    SUCCESS = "SUCCESS"
    FAILED  = "FAILED"
    SKIPPED = "SKIPPED"   # reserved for future use (circuit-breaker, feature flags)


@dataclass
class ConsumerResult:
    """
    Immutable record of one consumer's execution within an event dispatch cycle.

    Attributes:
        consumer_name:   Fully-qualified class name of the consumer.
        policy:          ExecutionPolicy declared by the consumer.
        priority:        Declared priority (higher = executes first in ORDERED group).
        status:          SUCCESS | FAILED | SKIPPED.
        duration_ms:     Wall-clock execution time in milliseconds.
        stage_index:     Stage the consumer ran in (0 = no-dependency stage).
                         None when run() (flat, no plan) is used.
        exception_type:  Exception class name if status=FAILED, else None.
        exception_msg:   Exception str() if status=FAILED, else None.
        traceback:       Full traceback string if status=FAILED, else None.
    """
    consumer_name:  str
    policy:         ExecutionPolicy
    priority:       int
    status:         ConsumerStatus
    duration_ms:    int
    stage_index:    Optional[int]      = None
    exception_type: Optional[str]      = None
    exception_msg:  Optional[str]      = None
    traceback:      Optional[str]      = None
    started_at:     Optional[datetime] = None
    finished_at:    Optional[datetime] = None

    @property
    def failed(self) -> bool:
        return self.status == ConsumerStatus.FAILED

    def to_dict(self) -> dict:
        return {
            "consumer":       self.consumer_name,
            "policy":         self.policy.value,
            "priority":       self.priority,
            "stage":          self.stage_index,
            "status":         self.status.value,
            "duration_ms":    self.duration_ms,
            "started_at":     self.started_at.isoformat() if self.started_at else None,
            "finished_at":    self.finished_at.isoformat() if self.finished_at else None,
            "exception_type": self.exception_type,
            "exception_msg":  self.exception_msg,
        }


@dataclass
class ExecutionReport:
    """
    Aggregated result of executing all consumers for a single event.

    Attributes:
        event_id:          UUID of the dispatched EventRecord.
        event_name:        Class name of the domain event.
        total_duration_ms: Wall-clock time from first consumer start to last
                           consumer finish (inclusive of sequential gaps).
        results:           Ordered list of ConsumerResult, one per consumer.
        has_errors:        True if any consumer returned status=FAILED.
        error_messages:    Flat list of "ConsumerName: error_msg" strings for
                           the LifecycleManager's error_detail field.
    """
    event_id:          UUID
    event_name:        str
    total_duration_ms: int
    results:           List[ConsumerResult]
    has_errors:        bool
    error_messages:    List[str]

    def error_detail(self) -> str:
        """Single string suitable for EventRecord.error_detail."""
        return "; ".join(self.error_messages)

    def summary(self) -> dict:
        """Structured dict for log emission."""
        return {
            "event_id":          str(self.event_id),
            "event_name":        self.event_name,
            "total_duration_ms": self.total_duration_ms,
            "has_errors":        self.has_errors,
            "consumers_total":   len(self.results),
            "consumers_failed":  sum(1 for r in self.results if r.failed),
            "consumers_ok":      sum(1 for r in self.results if not r.failed),
            "results":           [r.to_dict() for r in self.results],
        }


# ── Orchestrator ──────────────────────────────────────────────────────────────

class ConsumerOrchestrator:
    """
    Stateless consumer execution engine.

    All logic is in the single classmethod `run()`. The class exists purely
    as a namespace and to allow subclassing in tests.

    Execution order
    ───────────────
    Phase 1 — ORDERED + CRITICAL (serial, priority-sorted, highest first):
        Consumers run one at a time in declared priority order.
        If a CRITICAL consumer fails, the ordered chain halts immediately.
        A non-CRITICAL ORDERED failure records the error and continues.

    Phase 2 — PARALLEL (concurrent):
        All PARALLEL consumers run via asyncio.gather(return_exceptions=True).
        One failure does NOT cancel siblings.
        PARALLEL phase only runs if no CRITICAL failure occurred in Phase 1.
        (If a CRITICAL consumer failed, further processing is unsafe.)

    Phase 3 — BACKGROUND (concurrent, always runs):
        BACKGROUND consumers run via asyncio.gather(return_exceptions=True).
        They execute regardless of Phase 1 or Phase 2 outcomes.
        They represent fire-and-monitor side-effects that must not be gated.
    """

    @classmethod
    async def run(
        cls,
        event: UniversalBaseEvent,
        consumers: Sequence[EventConsumer],
        event_id: UUID,
    ) -> ExecutionReport:
        """
        Flat execution path — no dependency graph.

        All consumers are bucketed by ExecutionPolicy and run in
        Phase 1 / 2 / 3 order.  This is the backward-compatible entry point
        used when no consumer declares depends_on(), and also delegates to
        the inner stage execution logic used by run_plan().

        Args:
            event:     Reconstructed domain event object.
            consumers: All consumers registered for this event class.
            event_id:  UUID of the EventRecord (for log correlation).

        Returns:
            ExecutionReport with per-consumer results and aggregate status.
        """
        wall_start = time.monotonic()
        all_results, _ = await cls._execute_stage(
            event=event,
            consumers=list(consumers),
            event_id=event_id,
            stage_index=None,
        )
        wall_end  = time.monotonic()
        return cls._build_report(event, event_id, all_results, wall_start, wall_end)

    @classmethod
    async def run_plan(
        cls,
        event: UniversalBaseEvent,
        plan: "ExecutionPlan",
        event_id: UUID,
    ) -> ExecutionReport:
        """
        Stage-aware execution path — uses an ExecutionPlan produced by PlanBuilder.

        Stages are executed sequentially in topological order.  Within each
        stage the Phase 1/2/3 bucketing (ORDERED/CRITICAL → PARALLEL →
        BACKGROUND) still applies, so execution policy is always respected
        regardless of how many stages exist.

        Stage halt behaviour:
          • If a CRITICAL consumer fails in stage N, stages N+1… are skipped
            for ORDERED and PARALLEL consumers (their work is unsafe without
            the critical predecessor succeeding).
          • BACKGROUND consumers in skipped stages are deliberately NOT run
            because their dependency chain was broken — they are not
            fire-and-monitor side-effects in this context but proper dependents.

        Args:
            event:    Reconstructed domain event object.
            plan:     ExecutionPlan from PlanBuilder.build().
            event_id: UUID of the EventRecord.

        Returns:
            ExecutionReport with per-consumer results and aggregate status.
        """
        wall_start     = time.monotonic()
        all_results:   List[ConsumerResult] = []
        critical_failed = False

        for stage in plan.stages:
            stage_consumers = list(stage.consumers)

            if critical_failed:
                # Emit SKIPPED results for every consumer in the remaining stages
                for consumer in stage_consumers:
                    all_results.append(cls._make_skipped(consumer, stage.index))
                logger.warning(
                    "execution_plan_stage_skipped",
                    event_id=str(event_id),
                    event_name=event.event_name,
                    stage=stage.index,
                    reason="critical_failure_in_prior_stage",
                    skipped_consumers=[c.__class__.__name__ for c in stage_consumers],
                )
                continue

            logger.info(
                "execution_plan_stage_starting",
                event_id=str(event_id),
                event_name=event.event_name,
                stage=stage.index,
                consumers=[c.__class__.__name__ for c in stage_consumers],
            )

            stage_results, stage_critical_failed = await cls._execute_stage(
                event=event,
                consumers=stage_consumers,
                event_id=event_id,
                stage_index=stage.index,
            )
            all_results.extend(stage_results)

            if stage_critical_failed:
                critical_failed = True
                logger.error(
                    "execution_plan_stage_critical_failure",
                    event_id=str(event_id),
                    event_name=event.event_name,
                    failed_stage=stage.index,
                    remaining_stages=plan.stage_count - stage.index - 1,
                )

            logger.info(
                "execution_plan_stage_completed",
                event_id=str(event_id),
                event_name=event.event_name,
                stage=stage.index,
                consumers_ok=sum(1 for r in stage_results if not r.failed),
                consumers_failed=sum(1 for r in stage_results if r.failed),
            )

        wall_end = time.monotonic()
        return cls._build_report(event, event_id, all_results, wall_start, wall_end)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @classmethod
    async def _execute_stage(
        cls,
        event: UniversalBaseEvent,
        consumers: List[EventConsumer],
        event_id: UUID,
        stage_index: Optional[int],
    ) -> tuple[List[ConsumerResult], bool]:
        """
        Execute a flat list of consumers through Phase 1/2/3 bucketing.

        Returns:
            (results, critical_failed) — results is the per-consumer list;
            critical_failed is True if any CRITICAL consumer failed (used by
            run_plan to decide whether to halt subsequent stages).
        """
        ordered:    List[EventConsumer] = []
        parallel:   List[EventConsumer] = []
        background: List[EventConsumer] = []

        for c in consumers:
            policy = c.get_execution_policy()
            if policy in (ExecutionPolicy.ORDERED, ExecutionPolicy.CRITICAL):
                ordered.append(c)
            elif policy == ExecutionPolicy.PARALLEL:
                parallel.append(c)
            elif policy == ExecutionPolicy.BACKGROUND:
                background.append(c)

        ordered.sort(key=lambda c: c.get_priority(), reverse=True)

        stage_results:  List[ConsumerResult] = []
        critical_failed = False

        # Phase 1 — ORDERED + CRITICAL (serial)
        for consumer in ordered:
            result = await cls._run_one(event, consumer, event_id, stage_index)
            stage_results.append(result)
            if result.failed and consumer.get_execution_policy() == ExecutionPolicy.CRITICAL:
                critical_failed = True
                logger.error(
                    "consumer_critical_failure_halting_ordered_chain",
                    event_id=str(event_id),
                    event_name=event.event_name,
                    stage=stage_index,
                    consumer=result.consumer_name,
                    error=result.exception_msg,
                )
                break

        # Phase 2 — PARALLEL (skipped if CRITICAL failed)
        if parallel and not critical_failed:
            parallel_results = await cls._run_group(event, parallel, event_id, stage_index)
            stage_results.extend(parallel_results)
        elif parallel and critical_failed:
            logger.warning(
                "consumer_parallel_phase_skipped_due_to_critical_failure",
                event_id=str(event_id),
                stage=stage_index,
                skipped_count=len(parallel),
            )
            for consumer in parallel:
                stage_results.append(cls._make_skipped(consumer, stage_index))

        # Phase 3 — BACKGROUND (always runs)
        if background:
            bg_results = await cls._run_group(event, background, event_id, stage_index)
            stage_results.extend(bg_results)

        return stage_results, critical_failed

    @classmethod
    async def _run_one(
        cls,
        event: UniversalBaseEvent,
        consumer: EventConsumer,
        event_id: UUID,
        stage_index: Optional[int] = None,
    ) -> ConsumerResult:
        """
        Execute a single consumer and return its ConsumerResult.
        Never raises — all exceptions are captured into the result.
        """
        name     = consumer.__class__.__name__
        policy   = consumer.get_execution_policy()
        priority = consumer.get_priority()

        logger.info(
            "consumer_started",
            event_id=str(event_id),
            event_name=event.event_name,
            consumer=name,
            policy=policy.value,
            priority=priority,
            stage=stage_index,
        )

        from app.events.tracing import trace_manager
        span = trace_manager.start_span(
            component_name=f"consumer.{name}",
            operation_name="handle_event",
            tags={
                "consumer_name": name,
                "policy": policy.value,
                "stage_index": stage_index,
                "event_id": str(event_id),
            },
        )

        started_at = datetime.now(timezone.utc)
        t0 = time.monotonic()
        try:
            await consumer.handle_event(event)
            duration_ms = int((time.monotonic() - t0) * 1000)
            finished_at = datetime.now(timezone.utc)
            if span:
                trace_manager.finish_span(span)
            logger.info(
                "consumer_completed",
                event_id=str(event_id),
                consumer=name,
                policy=policy.value,
                stage=stage_index,
                duration_ms=duration_ms,
            )
            return ConsumerResult(
                consumer_name=name,
                policy=policy,
                priority=priority,
                status=ConsumerStatus.SUCCESS,
                duration_ms=duration_ms,
                stage_index=stage_index,
                started_at=started_at,
                finished_at=finished_at,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            finished_at = datetime.now(timezone.utc)
            tb = traceback.format_exc()
            if span:
                trace_manager.finish_span(span, error=exc)
            logger.error(
                "consumer_failed",
                event_id=str(event_id),
                event_name=event.event_name,
                consumer=name,
                policy=policy.value,
                stage=stage_index,
                duration_ms=duration_ms,
                exception_type=type(exc).__name__,
                exception_msg=str(exc),
            )
            return ConsumerResult(
                consumer_name=name,
                policy=policy,
                priority=priority,
                status=ConsumerStatus.FAILED,
                duration_ms=duration_ms,
                stage_index=stage_index,
                exception_type=type(exc).__name__,
                exception_msg=str(exc),
                traceback=tb,
                started_at=started_at,
                finished_at=finished_at,
            )

    @classmethod
    async def _run_group(
        cls,
        event: UniversalBaseEvent,
        consumers: List[EventConsumer],
        event_id: UUID,
        stage_index: Optional[int] = None,
    ) -> List[ConsumerResult]:
        """
        Execute a group of consumers concurrently via asyncio.gather.
        return_exceptions=True guarantees all consumers run to completion
        regardless of sibling failures.
        """
        tasks   = [cls._run_one(event, c, event_id, stage_index) for c in consumers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: List[ConsumerResult] = []
        for consumer, result in zip(consumers, results):
            if isinstance(result, ConsumerResult):
                output.append(result)
            else:
                # asyncio.gather surfaced a bare exception (e.g. CancelledError)
                name = consumer.__class__.__name__
                output.append(ConsumerResult(
                    consumer_name=name,
                    policy=consumer.get_execution_policy(),
                    priority=consumer.get_priority(),
                    status=ConsumerStatus.FAILED,
                    duration_ms=0,
                    stage_index=stage_index,
                    exception_type=type(result).__name__,
                    exception_msg=str(result),
                ))
        return output

    @staticmethod
    def _make_skipped(consumer: EventConsumer, stage_index: Optional[int]) -> ConsumerResult:
        """Return a SKIPPED ConsumerResult for a consumer that was not executed."""
        return ConsumerResult(
            consumer_name=consumer.__class__.__name__,
            policy=consumer.get_execution_policy(),
            priority=consumer.get_priority(),
            status=ConsumerStatus.SKIPPED,
            duration_ms=0,
            stage_index=stage_index,
        )

    @staticmethod
    def _build_report(
        event: UniversalBaseEvent,
        event_id: UUID,
        all_results: List[ConsumerResult],
        wall_start: float,
        wall_end: float,
    ) -> ExecutionReport:
        """Assemble the final ExecutionReport and emit the summary log."""
        total_ms   = int((wall_end - wall_start) * 1000)
        has_errors = any(r.failed for r in all_results)
        error_msgs = [
            f"{r.consumer_name}: {r.exception_msg}"
            for r in all_results if r.failed
        ]
        report = ExecutionReport(
            event_id=event_id,
            event_name=event.event_name,
            total_duration_ms=total_ms,
            results=all_results,
            has_errors=has_errors,
            error_messages=error_msgs,
        )
        log_fn = logger.warning if has_errors else logger.info
        log_fn("event_execution_report", **report.summary())
        return report
