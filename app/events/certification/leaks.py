"""
HunterOS Engage — Resource Leak & Lifecycle Verifier
app/events/certification/leaks.py

Provides automated verification confirming:
- No memory leaks
- No thread leaks
- No asyncio task leaks
- No orphan locks
- No orphan workers
- No stale dispatcher registrations
- No unreleased leader leases
"""

import asyncio
import gc
import threading
import tracemalloc
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from app.events.certification.config import ResourceLeakLimits, certification_config
from app.events.cluster.coordinator import default_cluster_coordinator
from app.events.partitioning.lock_manager import get_lock_manager


@dataclass
class LeakCheckItem:
    """Individual resource leak evaluation outcome."""
    resource_type: str
    baseline_value: Any
    final_value: Any
    delta_value: Any
    allowed_limit: Any
    passed: bool
    details: str = ""


@dataclass
class ResourceCertificationReport:
    """Comprehensive resource leak certification report."""
    passed: bool
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: List[LeakCheckItem] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)


class ResourceLeakDetector:
    """
    Measures and certifies that runtime execution cleanly releases all allocated resources.
    """

    def __init__(self, limits: Optional[ResourceLeakLimits] = None):
        self._limits = limits or certification_config.leaks
        self._baseline_state: Dict[str, Any] = {}

    def capture_baseline(self) -> Dict[str, Any]:
        """Capture baseline metrics before running load/chaos operations."""
        gc.collect()
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        active_threads = threading.active_count()
        
        try:
            active_tasks = len(asyncio.all_tasks())
        except RuntimeError:
            active_tasks = 0

        active_locks = len(get_lock_manager().get_active_locks())
        active_dispatchers = len(default_cluster_coordinator.registry.get_cluster())
        has_unreleased_lease = default_cluster_coordinator.lease_manager.get_current_leader() is not None

        self._baseline_state = {
            "memory_bytes": current_mem,
            "active_threads": active_threads,
            "active_tasks": active_tasks,
            "active_locks": active_locks,
            "active_dispatchers": active_dispatchers,
            "has_unreleased_lease": has_unreleased_lease,
        }
        return dict(self._baseline_state)

    def evaluate_leaks(self) -> ResourceCertificationReport:
        """
        Compare current system state against baseline and evaluate strict leak limits.
        """
        gc.collect()
        current_mem, _ = tracemalloc.get_traced_memory() if tracemalloc.is_tracing() else (0, 0)
        active_threads = threading.active_count()
        
        try:
            active_tasks = len(asyncio.all_tasks())
        except RuntimeError:
            active_tasks = 0

        active_locks = len(get_lock_manager().get_active_locks())
        active_dispatchers = len(default_cluster_coordinator.registry.get_cluster())
        has_unreleased_lease = default_cluster_coordinator.lease_manager.get_current_leader() is not None

        b = self._baseline_state
        checks: List[LeakCheckItem] = []
        violations: List[str] = []

        # 1. Memory Growth (MB)
        baseline_mem = b.get("memory_bytes", current_mem)
        mem_growth_mb = max(0.0, (current_mem - baseline_mem) / (1024 * 1024))
        mem_passed = mem_growth_mb <= self._limits.max_memory_growth_mb
        checks.append(LeakCheckItem(
            resource_type="memory_growth_mb",
            baseline_value=f"{baseline_mem / (1024*1024):.2f}MB",
            final_value=f"{current_mem / (1024*1024):.2f}MB",
            delta_value=f"+{mem_growth_mb:.2f}MB",
            allowed_limit=f"<={self._limits.max_memory_growth_mb}MB",
            passed=mem_passed,
            details=f"Memory growth is {mem_growth_mb:.2f}MB (limit: {self._limits.max_memory_growth_mb}MB).",
        ))
        if not mem_passed:
            violations.append(f"Memory leak detected: growth of {mem_growth_mb:.2f}MB exceeds limit of {self._limits.max_memory_growth_mb}MB.")

        # 2. Thread Leaks
        baseline_threads = b.get("active_threads", active_threads)
        thread_delta = max(0, active_threads - baseline_threads)
        threads_passed = thread_delta <= self._limits.max_thread_leak_count
        checks.append(LeakCheckItem(
            resource_type="thread_leaks",
            baseline_value=baseline_threads,
            final_value=active_threads,
            delta_value=thread_delta,
            allowed_limit=self._limits.max_thread_leak_count,
            passed=threads_passed,
            details=f"Active threads changed from {baseline_threads} to {active_threads} (delta: {thread_delta}).",
        ))
        if not threads_passed:
            violations.append(f"Thread leak detected: {thread_delta} unclosed threads remaining.")

        # 3. Asyncio Task Leaks
        baseline_tasks = b.get("active_tasks", active_tasks)
        task_delta = max(0, active_tasks - baseline_tasks)
        tasks_passed = task_delta <= self._limits.max_asyncio_task_leak_count
        checks.append(LeakCheckItem(
            resource_type="asyncio_task_leaks",
            baseline_value=baseline_tasks,
            final_value=active_tasks,
            delta_value=task_delta,
            allowed_limit=self._limits.max_asyncio_task_leak_count,
            passed=tasks_passed,
            details=f"Asyncio tasks changed from {baseline_tasks} to {active_tasks} (delta: {task_delta}).",
        ))
        if not tasks_passed:
            violations.append(f"Asyncio task leak detected: {task_delta} hanging background tasks.")

        # 4. Orphan Locks
        orphan_locks = active_locks
        locks_passed = orphan_locks <= self._limits.max_orphan_locks_count
        checks.append(LeakCheckItem(
            resource_type="orphan_locks",
            baseline_value=b.get("active_locks", 0),
            final_value=active_locks,
            delta_value=orphan_locks,
            allowed_limit=self._limits.max_orphan_locks_count,
            passed=locks_passed,
            details=f"Active unreleased partition locks: {orphan_locks}.",
        ))
        if not locks_passed:
            violations.append(f"Orphan locks detected: {orphan_locks} unreleased partition locks.")

        # 5. Stale Dispatcher Registrations
        stale_dispatchers = active_dispatchers
        dispatchers_passed = stale_dispatchers <= self._limits.max_stale_dispatchers_count
        checks.append(LeakCheckItem(
            resource_type="stale_dispatchers",
            baseline_value=b.get("active_dispatchers", 0),
            final_value=active_dispatchers,
            delta_value=stale_dispatchers,
            allowed_limit=self._limits.max_stale_dispatchers_count,
            passed=dispatchers_passed,
            details=f"Active registered dispatchers: {stale_dispatchers}.",
        ))
        if not dispatchers_passed:
            violations.append(f"Stale dispatchers detected: {stale_dispatchers} nodes still registered.")

        # 6. Unreleased Leader Leases
        lease_passed = not (has_unreleased_lease and self._limits.max_unreleased_leases_count == 0 and not b.get("has_unreleased_lease", False))
        checks.append(LeakCheckItem(
            resource_type="unreleased_leader_leases",
            baseline_value=b.get("has_unreleased_lease", False),
            final_value=has_unreleased_lease,
            delta_value=1 if has_unreleased_lease else 0,
            allowed_limit=self._limits.max_unreleased_leases_count,
            passed=lease_passed,
            details=f"Leader lease state: {'Held' if has_unreleased_lease else 'Released'}.",
        ))
        if not lease_passed:
            violations.append("Unreleased cluster leadership lease detected after teardown.")

        passed_count = sum(1 for c in checks if c.passed)
        failed_count = len(checks) - passed_count
        overall_passed = failed_count == 0

        return ResourceCertificationReport(
            passed=overall_passed,
            total_checks=len(checks),
            passed_checks=passed_count,
            failed_checks=failed_count,
            checks=checks,
            violations=violations,
        )


# Global leak detector instance
leak_detector = ResourceLeakDetector()
