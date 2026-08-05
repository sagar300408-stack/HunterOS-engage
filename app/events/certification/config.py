"""
HunterOS Engage — Production Certification & Hardening Configuration
app/events/certification/config.py

Defines production readiness thresholds, deterministic performance budgets,
leak detection limits, soak test parameters, and configuration audit rules.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass(frozen=True)
class PerformanceBudgets:
    """
    Deterministic performance budgets enforced during certification.
    All times in milliseconds unless specified otherwise.
    """
    max_event_publish_p95_ms: float = 5.0
    max_dispatcher_planning_p95_ms: float = 10.0
    max_consumer_planning_ms: float = 5.0
    max_worker_overhead_ms: float = 2.0
    max_trace_overhead_per_span_ms: float = 0.05
    max_scheduler_planning_10k_events_ms: float = 20.0


@dataclass(frozen=True)
class ResourceLeakLimits:
    """
    Resource leak limits enforced during certification and soak testing.
    """
    max_memory_growth_mb: float = 50.0
    max_thread_leak_count: int = 0
    max_asyncio_task_leak_count: int = 0
    max_orphan_locks_count: int = 0
    max_orphan_workers_count: int = 0
    max_stale_dispatchers_count: int = 0
    max_unreleased_leases_count: int = 0


@dataclass(frozen=True)
class SoakTestConfig:
    """
    Soak testing simulation parameters.
    """
    simulated_hours: int = 24
    simulated_events_per_second: int = 500
    acceleration_factor: int = 1000  # Enables rapid testing while maintaining logical cycle fidelity
    max_allowed_throughput_degradation_pct: float = 5.0
    max_allowed_latency_drift_pct: float = 10.0


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """
    Circuit breaker thresholds for downstream event delivery.
    """
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_consecutive_successes: int = 3


@dataclass(frozen=True)
class ProductionCertificationConfig:
    """
    Central production certification configuration container.
    """
    budgets: PerformanceBudgets = field(default_factory=PerformanceBudgets)
    leaks: ResourceLeakLimits = field(default_factory=ResourceLeakLimits)
    soak: SoakTestConfig = field(default_factory=SoakTestConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # Sensitive field names to redact/mask
    sensitive_keys: List[str] = field(default_factory=lambda: [
        "password",
        "secret",
        "token",
        "authorization",
        "api_key",
        "access_token",
        "refresh_token",
        "private_key",
        "credit_card",
        "ssn",
        "cvv",
        "email",
        "phone",
    ])
    
    # Mandatory production configuration audit requirements
    require_debug_disabled: bool = True
    require_tls: bool = True
    min_db_pool_size: int = 5
    max_db_pool_size: int = 50
    min_worker_concurrency: int = 2
    max_worker_concurrency: int = 64
    max_lock_timeout_seconds: int = 120
    min_heartbeat_interval_seconds: int = 1
    max_heartbeat_interval_seconds: int = 30


# Global singleton configuration instance
certification_config = ProductionCertificationConfig()
