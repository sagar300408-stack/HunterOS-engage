"""
HunterOS Engage — Runtime Diagnostics Configuration
app/events/diagnostics/config.py

Thread-safe configuration for runtime diagnostics, live monitoring,
and subsystem operational inspection.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticsConfig:
    """
    Configuration for runtime diagnostics, health monitoring, and live inspection.
    Supports environment variable overrides for zero-code configuration in production.
    """
    enabled: bool = True
    snapshot_cache_ttl_seconds: float = 1.0
    worker_stale_threshold_seconds: float = 30.0
    dispatcher_stale_threshold_seconds: float = 15.0
    lock_stale_threshold_seconds: float = 30.0
    queue_high_watermark: int = 1000
    consumer_slow_threshold_ms: float = 200.0
    partition_hotspot_threshold: int = 50
    max_inspected_items: int = 100
    health_warning_threshold: int = 70
    health_critical_threshold: int = 40

    @classmethod
    def from_env(cls) -> DiagnosticsConfig:
        """
        Builds a DiagnosticsConfig instance from environment variables with safe defaults.
        """
        def _get_bool(key: str, default: bool) -> bool:
            val = os.getenv(key)
            if val is None:
                return default
            return val.strip().lower() in ("1", "true", "yes", "on")

        def _get_float(key: str, default: float) -> float:
            val = os.getenv(key)
            if val is None:
                return default
            try:
                return float(val.strip())
            except ValueError:
                return default

        def _get_int(key: str, default: int) -> int:
            val = os.getenv(key)
            if val is None:
                return default
            try:
                return int(val.strip())
            except ValueError:
                return default

        return cls(
            enabled=_get_bool("HUNTEROS_DIAGNOSTICS_ENABLED", True),
            snapshot_cache_ttl_seconds=_get_float("HUNTEROS_DIAGNOSTICS_SNAPSHOT_CACHE_TTL_SECONDS", 1.0),
            worker_stale_threshold_seconds=_get_float("HUNTEROS_DIAGNOSTICS_WORKER_STALE_THRESHOLD_SECONDS", 30.0),
            dispatcher_stale_threshold_seconds=_get_float("HUNTEROS_DIAGNOSTICS_DISPATCHER_STALE_THRESHOLD_SECONDS", 15.0),
            lock_stale_threshold_seconds=_get_float("HUNTEROS_DIAGNOSTICS_LOCK_STALE_THRESHOLD_SECONDS", 30.0),
            queue_high_watermark=_get_int("HUNTEROS_DIAGNOSTICS_QUEUE_HIGH_WATERMARK", 1000),
            consumer_slow_threshold_ms=_get_float("HUNTEROS_DIAGNOSTICS_CONSUMER_SLOW_THRESHOLD_MS", 200.0),
            partition_hotspot_threshold=_get_int("HUNTEROS_DIAGNOSTICS_PARTITION_HOTSPOT_THRESHOLD", 50),
            max_inspected_items=_get_int("HUNTEROS_DIAGNOSTICS_MAX_INSPECTED_ITEMS", 100),
            health_warning_threshold=_get_int("HUNTEROS_DIAGNOSTICS_HEALTH_WARNING_THRESHOLD", 70),
            health_critical_threshold=_get_int("HUNTEROS_DIAGNOSTICS_HEALTH_CRITICAL_THRESHOLD", 40),
        )
