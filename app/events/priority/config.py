"""
HunterOS Engage — Priority & Flow Control Configuration
app/events/priority/config.py

Operational configuration with environment variable bindings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PriorityConfig:
    """
    Configuration parameters for Priority Scheduling, Virtual Aging, and Adaptive Backpressure.
    """
    enable_priority_scheduling: bool = True
    enable_priority_aging: bool = True
    aging_threshold_seconds: float = 30.0
    aging_step_seconds: float = 15.0
    max_aging_boost: int = 2

    # Backpressure & Load Thresholds
    enable_backpressure: bool = True
    queue_depth_normal_threshold: int = 500
    queue_depth_busy_threshold: int = 1500
    queue_depth_high_load_threshold: int = 3000
    queue_depth_saturated_threshold: int = 5000

    target_dispatch_latency_ms: float = 200.0
    max_worker_utilization_ratio: float = 0.85

    @classmethod
    def from_env(cls) -> PriorityConfig:
        """Loads configuration from environment variables with safe defaults."""
        return cls(
            enable_priority_scheduling=os.getenv("PRIORITY_SCHEDULING_ENABLED", "true").lower() in ("true", "1", "yes"),
            enable_priority_aging=os.getenv("PRIORITY_AGING_ENABLED", "true").lower() in ("true", "1", "yes"),
            aging_threshold_seconds=float(os.getenv("PRIORITY_AGING_THRESHOLD_SECONDS", "30.0")),
            aging_step_seconds=float(os.getenv("PRIORITY_AGING_STEP_SECONDS", "15.0")),
            max_aging_boost=int(os.getenv("MAX_PRIORITY_AGING_BOOST", "2")),
            enable_backpressure=os.getenv("BACKPRESSURE_ENABLED", "true").lower() in ("true", "1", "yes"),
            queue_depth_normal_threshold=int(os.getenv("QUEUE_DEPTH_NORMAL_THRESHOLD", "500")),
            queue_depth_busy_threshold=int(os.getenv("QUEUE_DEPTH_BUSY_THRESHOLD", "1500")),
            queue_depth_high_load_threshold=int(os.getenv("QUEUE_DEPTH_HIGH_LOAD_THRESHOLD", "3000")),
            queue_depth_saturated_threshold=int(os.getenv("QUEUE_DEPTH_SATURATED_THRESHOLD", "5000")),
            target_dispatch_latency_ms=float(os.getenv("TARGET_DISPATCH_LATENCY_MS", "200.0")),
            max_worker_utilization_ratio=float(os.getenv("MAX_WORKER_UTILIZATION_RATIO", "0.85")),
        )
