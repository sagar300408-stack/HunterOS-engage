"""
Configuration Layer for Event Partitioning & Scheduling in HunterOS Engage.
"""

import os
from pydantic import BaseModel, Field


class PartitionConfig(BaseModel):
    """
    Operational configuration for event partitioning, locking, and fair scheduling.
    """
    partition_batch_size: int = Field(
        default_factory=lambda: int(os.getenv("PARTITION_BATCH_SIZE", "50")),
        description="Maximum total events scheduled per dispatcher cycle.",
    )
    max_active_partitions: int = Field(
        default_factory=lambda: int(os.getenv("MAX_ACTIVE_PARTITIONS", "100")),
        description="Maximum number of distinct partitions concurrently eligible for dispatch.",
    )
    max_events_per_partition_per_cycle: int = Field(
        default_factory=lambda: int(os.getenv("MAX_EVENTS_PER_PARTITION_PER_CYCLE", "5")),
        description="Maximum events dispatched for any single partition in a single scheduler cycle (prevents starvation).",
    )
    lock_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("PARTITION_LOCK_TIMEOUT_SECONDS", "60.0")),
        description="Default lease duration in seconds for partition locks.",
    )
    scheduler_interval_ms: int = Field(
        default_factory=lambda: int(os.getenv("PARTITION_SCHEDULER_INTERVAL_MS", "1000")),
        description="Polling interval for partition scheduler in milliseconds.",
    )
    fairness_policy: str = Field(
        default_factory=lambda: os.getenv("PARTITION_FAIRNESS_POLICY", "ROUND_ROBIN"),
        description="Scheduling policy for partition fairness: 'ROUND_ROBIN', 'DEFICIT_ROUND_ROBIN', or 'FIFO'.",
    )


# Global singleton instance
partition_config = PartitionConfig()
