"""
HunterOS Engage — Execution Intelligence Configuration
app/events/intelligence/config.py

Configures performance thresholds, pattern detection parameters,
health scoring decay factors, and historical window boundaries.
"""

from dataclasses import dataclass
import os


@dataclass
class IntelligenceConfig:
    """
    Configuration parameters for the Execution Intelligence Engine.
    All parameters have production defaults and can be overridden via environment variables.
    """

    enabled: bool = True
    slow_consumer_threshold_ms: float = 100.0
    slow_dispatcher_threshold_ms: float = 50.0
    slow_queue_threshold_ms: float = 150.0
    slow_worker_threshold_ms: float = 200.0
    slow_database_threshold_ms: float = 50.0

    # Bottleneck ratios (e.g. if component duration > 40% of total trace latency)
    component_bottleneck_ratio_threshold: float = 0.40

    # Hotspot and skew thresholds
    partition_hotspot_ratio: float = 0.30
    worker_hotspot_ratio: float = 0.40
    dispatcher_hotspot_ratio: float = 0.50

    # Pattern detection thresholds
    retry_storm_threshold: int = 5
    repeated_failure_threshold: int = 3
    recurring_slow_consumer_threshold: int = 3

    # Anomaly detection (Z-score threshold)
    anomaly_z_score_threshold: float = 2.5

    # Health scoring decay & weights
    health_decay_factor: float = 0.95
    historical_window_size: int = 1000
    max_recommendations: int = 50
    max_stored_root_causes: int = 200
    max_stored_bottlenecks: int = 200

    @classmethod
    def from_env(cls) -> "IntelligenceConfig":
        """Constructs configuration from environment variables."""
        return cls(
            enabled=os.getenv("HUNTER_INTELLIGENCE_ENABLED", "true").lower() in ("1", "true", "yes"),
            slow_consumer_threshold_ms=float(os.getenv("HUNTER_INTELLIGENCE_SLOW_CONSUMER_MS", "100.0")),
            slow_dispatcher_threshold_ms=float(os.getenv("HUNTER_INTELLIGENCE_SLOW_DISPATCHER_MS", "50.0")),
            slow_queue_threshold_ms=float(os.getenv("HUNTER_INTELLIGENCE_SLOW_QUEUE_MS", "150.0")),
            slow_worker_threshold_ms=float(os.getenv("HUNTER_INTELLIGENCE_SLOW_WORKER_MS", "200.0")),
            slow_database_threshold_ms=float(os.getenv("HUNTER_INTELLIGENCE_SLOW_DB_MS", "50.0")),
            component_bottleneck_ratio_threshold=float(os.getenv("HUNTER_INTELLIGENCE_BOTTLENECK_RATIO", "0.40")),
            partition_hotspot_ratio=float(os.getenv("HUNTER_INTELLIGENCE_PARTITION_HOTSPOT_RATIO", "0.30")),
            worker_hotspot_ratio=float(os.getenv("HUNTER_INTELLIGENCE_WORKER_HOTSPOT_RATIO", "0.40")),
            dispatcher_hotspot_ratio=float(os.getenv("HUNTER_INTELLIGENCE_DISPATCHER_HOTSPOT_RATIO", "0.50")),
            retry_storm_threshold=int(os.getenv("HUNTER_INTELLIGENCE_RETRY_STORM_THRESHOLD", "5")),
            repeated_failure_threshold=int(os.getenv("HUNTER_INTELLIGENCE_REPEATED_FAILURE_THRESHOLD", "3")),
            recurring_slow_consumer_threshold=int(os.getenv("HUNTER_INTELLIGENCE_RECURRING_SLOW_CONSUMER_THRESHOLD", "3")),
            anomaly_z_score_threshold=float(os.getenv("HUNTER_INTELLIGENCE_ANOMALY_Z_SCORE", "2.5")),
            health_decay_factor=float(os.getenv("HUNTER_INTELLIGENCE_HEALTH_DECAY", "0.95")),
            historical_window_size=int(os.getenv("HUNTER_INTELLIGENCE_HISTORY_WINDOW", "1000")),
            max_recommendations=int(os.getenv("HUNTER_INTELLIGENCE_MAX_RECOMMENDATIONS", "50")),
            max_stored_root_causes=int(os.getenv("HUNTER_INTELLIGENCE_MAX_ROOT_CAUSES", "200")),
            max_stored_bottlenecks=int(os.getenv("HUNTER_INTELLIGENCE_MAX_BOTTLENECKS", "200")),
        )
