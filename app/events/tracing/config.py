"""
HunterOS Engage — Distributed Tracing Configuration
app/events/tracing/config.py
"""

from dataclasses import dataclass, field
import os
from typing import Optional


@dataclass(frozen=True)
class TraceConfig:
    """
    Configuration for the Distributed Tracing and Execution Observability Subsystem.
    All properties are immutable and can be populated from environment variables.
    """

    enabled: bool = True
    max_span_depth: int = 32
    max_spans_per_trace: int = 500
    max_trace_retention: int = 10000
    retention_ttl_seconds: float = 86400.0  # 24 hours
    sampling_rate: float = 1.0  # 1.0 = 100% trace capture
    sampling_strategy: str = "always_on"  # "always_on" | "probabilistic" | "rate_limiting"
    compression_enabled: bool = False
    exporter_type: str = "in_memory"  # "in_memory" | "opentelemetry" | "console" | "noop"
    exporter_endpoint: Optional[str] = None

    @classmethod
    def from_env(cls) -> "TraceConfig":
        """Builds a TraceConfig instance from environment variables with safe fallbacks."""
        enabled_str = os.getenv("HUNTER_TRACING_ENABLED", "true").lower()
        enabled = enabled_str in ("1", "true", "yes", "on")

        max_depth = int(os.getenv("HUNTER_TRACING_MAX_DEPTH", "32"))
        max_spans = int(os.getenv("HUNTER_TRACING_MAX_SPANS", "500"))
        max_retention = int(os.getenv("HUNTER_TRACING_MAX_RETENTION", "10000"))
        retention_ttl = float(os.getenv("HUNTER_TRACING_RETENTION_TTL", "86400.0"))
        sampling_rate = float(os.getenv("HUNTER_TRACING_SAMPLING_RATE", "1.0"))
        sampling_strategy = os.getenv("HUNTER_TRACING_SAMPLING_STRATEGY", "always_on")
        compression = os.getenv("HUNTER_TRACING_COMPRESSION", "false").lower() in ("1", "true", "yes")
        exporter_type = os.getenv("HUNTER_TRACING_EXPORTER_TYPE", "in_memory")
        exporter_endpoint = os.getenv("HUNTER_TRACING_EXPORTER_ENDPOINT", None)

        return cls(
            enabled=enabled,
            max_span_depth=max_depth,
            max_spans_per_trace=max_spans,
            max_trace_retention=max_retention,
            retention_ttl_seconds=retention_ttl,
            sampling_rate=sampling_rate,
            sampling_strategy=sampling_strategy,
            compression_enabled=compression,
            exporter_type=exporter_type,
            exporter_endpoint=exporter_endpoint,
        )
