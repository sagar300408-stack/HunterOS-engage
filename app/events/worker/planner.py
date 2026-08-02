"""
HunterOS Engage — Consumer Dependency Graph & Execution Planner
app/events/worker/planner.py

Builds an immutable, topologically-sorted ExecutionPlan from a flat list
of EventConsumer instances by:

  1. Validating the consumer set (duplicates, missing deps)
  2. Constructing a directed acyclic graph (DAG) from each consumer's
     depends_on() declaration
  3. Computing execution stages via Kahn's topological-sort algorithm
  4. Detecting cycles (Kahn invariant: remaining nodes → cycle)
  5. Emitting a structured startup log of the full plan

The plan is then consumed by ConsumerOrchestrator.run_plan() which
executes stages sequentially and consumers within each stage according
to their ExecutionPolicy.

Algorithm: Kahn's BFS Topological Sort → Stages
────────────────────────────────────────────────
Given nodes V and directed edges E (B→A means "B depends on A"):

  in_degree[v] = number of A's that v directly depends on

  Stage 0 = { v | in_degree[v] == 0 }   (no dependencies)
  After processing stage S:
      For each v in S, for each w that depends on v:
          in_degree[w] -= 1
          if in_degree[w] == 0: add w to stage S+1
  Continue until all nodes are processed.
  If any nodes remain unprocessed → cycle detected.

Correctness:
  • A node appears in exactly one stage.
  • All dependencies of a node appear in strictly earlier stages.
  • Nodes within the same stage have no ordering constraint between them.
  • Determinism is guaranteed by sorting within each stage bucket
    (alphabetically by consumer class name) before finalising the stage.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Type

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Validation errors ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlanValidationError:
    """A single validation finding from PlanBuilder._validate()."""
    code: str          # DUPLICATE_CONSUMER | MISSING_DEPENDENCY | INVALID_POLICY_COMBO
    message: str
    consumers: Tuple[str, ...]   # consumer name(s) involved

    def to_dict(self) -> dict:
        return {
            "code":      self.code,
            "message":   self.message,
            "consumers": list(self.consumers),
        }


class PlanValidationFailed(Exception):
    """
    Raised by PlanBuilder.build() when one or more validation checks fail.
    The errors attribute contains the full list of PlanValidationError instances.
    """
    def __init__(self, errors: List[PlanValidationError]) -> None:
        self.errors = errors
        combined = "; ".join(e.message for e in errors)
        super().__init__(f"Execution plan validation failed: {combined}")


# ── Execution plan ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExecutionStage:
    """
    One stage in the execution plan.

    All consumers in a stage may run concurrently (subject to their
    ExecutionPolicy); the stage itself must complete before the next
    stage begins.

    Attributes:
        index:     Zero-based stage index (0 = first to run).
        consumers: Tuple of consumer instances in this stage, sorted
                   deterministically by (priority desc, class name asc).
    """
    index:     int
    consumers: Tuple[EventConsumer, ...]

    def describe(self) -> dict:
        return {
            "stage": self.index,
            "consumers": [
                {
                    "name":       c.__class__.__name__,
                    "policy":     c.get_execution_policy().value,
                    "priority":   c.get_priority(),
                    "depends_on": [cls.__name__ for cls in c.depends_on()],
                }
                for c in self.consumers
            ],
        }


@dataclass(frozen=True)
class ExecutionPlan:
    """
    Immutable, topologically-sorted execution plan for a set of consumers
    bound to a specific event class.

    Created once per (event_class, consumer_set) at dispatch time and
    consumed immediately by ConsumerOrchestrator.run_plan().

    Attributes:
        event_name:      Name of the event class this plan serves.
        stages:          Tuple of ExecutionStage, ordered for execution.
        edges:           All declared dependency edges (dependent, dependency)
                         as class-name pairs — for log/audit use only.
        consumer_count:  Total number of consumers in the plan.
    """
    event_name:     str
    stages:         Tuple[ExecutionStage, ...]
    edges:          Tuple[Tuple[str, str], ...]   # (dependent_name, dep_name)
    consumer_count: int

    @property
    def stage_count(self) -> int:
        return len(self.stages)

    @property
    def flat_consumers(self) -> List[EventConsumer]:
        """All consumers in stage order (for backward-compat with run())."""
        return [c for stage in self.stages for c in stage.consumers]

    def describe(self) -> dict:
        """Structured description emitted to the structured log at plan-build time."""
        return {
            "event_name":     self.event_name,
            "stage_count":    self.stage_count,
            "consumer_count": self.consumer_count,
            "dependency_edges": [
                f"{dependent} → {dep}"
                for dependent, dep in self.edges
            ],
            "stages": [s.describe() for s in self.stages],
        }


# ── Plan builder ──────────────────────────────────────────────────────────────

class PlanBuilder:
    """
    Constructs an ExecutionPlan from a flat list of EventConsumer instances.

    Usage:
        plan = PlanBuilder.build(event_name="RawWebhookEvent", consumers=consumers)

    Raises:
        PlanValidationFailed — if any validation check fails.
                               The error list contains ALL failures found,
                               not just the first, so they can all be fixed
                               in one iteration.
    """

    @classmethod
    def build(
        cls,
        event_name: str,
        consumers: List[EventConsumer],
    ) -> ExecutionPlan:
        """
        Validate → Build DAG → Topological sort → Return ExecutionPlan.

        Args:
            event_name: Name of the event class (for logging).
            consumers:  All consumers registered for this event class.

        Returns:
            Immutable ExecutionPlan ready for ConsumerOrchestrator.run_plan().

        Raises:
            PlanValidationFailed — on any validation failure.
        """
        # ── Step 1: Validate ──────────────────────────────────────────────────
        errors = cls._validate(consumers)
        if errors:
            for err in errors:
                logger.error(
                    "execution_plan_validation_error",
                    event_name=event_name,
                    **err.to_dict(),
                )
            raise PlanValidationFailed(errors)

        # ── Step 2: Build name→consumer index ────────────────────────────────
        # Consumer class name is the canonical node key.  Two instances of the
        # same class would be caught as DUPLICATE in validation above.
        name_to_consumer: Dict[str, EventConsumer] = {
            c.__class__.__name__: c for c in consumers
        }
        all_names: Set[str] = set(name_to_consumer)

        # ── Step 3: Build adjacency & in-degree structures ────────────────────
        # dependents[A] = list of B's that declared depends_on=[..., A, ...]
        # in_degree[B]  = number of direct dependencies B has
        dependents:  Dict[str, List[str]] = defaultdict(list)
        in_degree:   Dict[str, int]       = {name: 0 for name in all_names}
        edges:       List[Tuple[str, str]] = []

        for consumer in consumers:
            cname = consumer.__class__.__name__
            for dep_cls in consumer.depends_on():
                dep_name = dep_cls.__name__
                in_degree[cname] += 1
                dependents[dep_name].append(cname)
                edges.append((cname, dep_name))

        # ── Step 4: Kahn's BFS → stages ──────────────────────────────────────
        # Seeds: every consumer with no dependencies (in_degree == 0).
        # Sort for determinism so the plan is stable across runs.
        queue: deque[str] = deque(
            sorted(name for name, deg in in_degree.items() if deg == 0)
        )
        stages:    List[ExecutionStage] = []
        processed: Set[str]             = set()

        while queue:
            # All nodes currently in the queue form one stage.
            # Drain the queue atomically to capture the full stage.
            stage_names = list(queue)
            queue.clear()

            # Sort within stage: highest priority first, then alpha for ties.
            stage_names.sort(
                key=lambda n: (-name_to_consumer[n].get_priority(), n)
            )

            stage_consumers = tuple(name_to_consumer[n] for n in stage_names)
            stages.append(ExecutionStage(index=len(stages), consumers=stage_consumers))
            processed.update(stage_names)

            # Unlock dependents: reduce in_degree for every consumer that
            # depended on something just processed.
            next_ready: List[str] = []
            for name in stage_names:
                for dependent in dependents[name]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_ready.append(dependent)

            # Sort next batch for determinism before enqueuing.
            for name in sorted(set(next_ready)):
                queue.append(name)

        # ── Step 5: Cycle check (Kahn invariant) ─────────────────────────────
        remaining = all_names - processed
        if remaining:
            cycle_names = tuple(sorted(remaining))
            raise PlanValidationFailed([
                PlanValidationError(
                    code="CIRCULAR_DEPENDENCY",
                    message=(
                        "Circular dependency detected. The following consumers "
                        f"form a cycle and cannot be topologically sorted: "
                        f"{sorted(remaining)}"
                    ),
                    consumers=cycle_names,
                )
            ])

        # ── Step 6: Build and log the plan ────────────────────────────────────
        plan = ExecutionPlan(
            event_name=event_name,
            stages=tuple(stages),
            edges=tuple(edges),
            consumer_count=len(consumers),
        )

        logger.info(
            "execution_plan_built",
            **plan.describe(),
        )

        return plan

    # ── Validation ────────────────────────────────────────────────────────────

    @classmethod
    def _validate(cls, consumers: List[EventConsumer]) -> List[PlanValidationError]:
        """
        Run all pre-flight validation checks.  Returns every error found
        (not just the first) so callers can fix all issues in one pass.

        Checks:
          DUPLICATE_CONSUMER     — same class registered more than once
          MISSING_DEPENDENCY     — depends_on references a non-registered class
          INVALID_POLICY_COMBO   — BACKGROUND consumer is depended on by
                                   ORDERED/CRITICAL (would invert execution order)
        """
        errors:       List[PlanValidationError] = []
        seen_classes: Set[str]                   = set()
        all_names:    Set[str]                   = {c.__class__.__name__ for c in consumers}
        name_to_policy: Dict[str, ExecutionPolicy] = {
            c.__class__.__name__: c.get_execution_policy() for c in consumers
        }

        for consumer in consumers:
            cname  = consumer.__class__.__name__
            policy = consumer.get_execution_policy()

            # ── Duplicate check ────────────────────────────────────────────
            if cname in seen_classes:
                errors.append(PlanValidationError(
                    code="DUPLICATE_CONSUMER",
                    message=(
                        f"Consumer '{cname}' is registered more than once for "
                        "the same event class. Each consumer class may appear "
                        "at most once per event."
                    ),
                    consumers=(cname,),
                ))
            seen_classes.add(cname)

            for dep_cls in consumer.depends_on():
                dep_name = dep_cls.__name__

                # ── Missing dependency check ───────────────────────────────
                if dep_name not in all_names:
                    errors.append(PlanValidationError(
                        code="MISSING_DEPENDENCY",
                        message=(
                            f"Consumer '{cname}' declares depends_on=[{dep_name}] "
                            f"but '{dep_name}' is not registered for this event. "
                            "All declared dependencies must be registered consumers."
                        ),
                        consumers=(cname, dep_name),
                    ))
                    continue

                # ── Policy combination check ───────────────────────────────
                # A BACKGROUND consumer runs unconditionally in Phase 3 of
                # its stage, AFTER ORDERED/PARALLEL phases.  If a non-BACKGROUND
                # consumer declares depends_on=[SomeBackgroundConsumer], the
                # dependency is logically inverted — the depender would be
                # placed in a later stage than the BACKGROUND consumer it
                # "depends on", which is never what the author intends.
                dep_policy = name_to_policy.get(dep_name)
                if (
                    dep_policy == ExecutionPolicy.BACKGROUND
                    and policy in (ExecutionPolicy.ORDERED, ExecutionPolicy.CRITICAL)
                ):
                    errors.append(PlanValidationError(
                        code="INVALID_POLICY_COMBO",
                        message=(
                            f"Consumer '{cname}' (policy={policy.value}) declares "
                            f"depends_on=[{dep_name}] but '{dep_name}' has policy "
                            "BACKGROUND. BACKGROUND consumers are fire-and-monitor "
                            "side-effects and should not be declared as dependencies "
                            "of ORDERED or CRITICAL consumers."
                        ),
                        consumers=(cname, dep_name),
                    ))

        return errors
