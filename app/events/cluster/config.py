"""
Configuration for HunterOS Distributed Dispatcher Cluster Coordination.
"""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ClusterConfig:
    """
    Type-safe configuration for Distributed Dispatcher Cluster Coordination.
    Loaded from environment variables with production-grade defaults.
    """
    heartbeat_interval_seconds: float = 3.0
    leader_lease_seconds: float = 10.0
    node_timeout_seconds: float = 15.0
    max_cluster_size: int = 100
    ownership_hash_algorithm: str = "sha256"
    leader_renew_interval: float = 3.0
    auto_failover_enabled: bool = True
    virtual_nodes_per_dispatcher: int = 128

    @classmethod
    def from_env(cls) -> "ClusterConfig":
        """Loads cluster configuration from environment variables with fallbacks."""
        return cls(
            heartbeat_interval_seconds=float(
                os.getenv("DISPATCHER_HEARTBEAT_INTERVAL_SECONDS", "3.0")
            ),
            leader_lease_seconds=float(
                os.getenv("DISPATCHER_LEADER_LEASE_SECONDS", "10.0")
            ),
            node_timeout_seconds=float(
                os.getenv("DISPATCHER_NODE_TIMEOUT_SECONDS", "15.0")
            ),
            max_cluster_size=int(
                os.getenv("DISPATCHER_MAX_CLUSTER_SIZE", "100")
            ),
            ownership_hash_algorithm=os.getenv(
                "DISPATCHER_HASH_ALGORITHM", "sha256"
            ).lower(),
            leader_renew_interval=float(
                os.getenv("DISPATCHER_LEADER_RENEW_INTERVAL", "3.0")
            ),
            auto_failover_enabled=os.getenv(
                "DISPATCHER_AUTO_FAILOVER_ENABLED", "true"
            ).lower() == "true",
            virtual_nodes_per_dispatcher=int(
                os.getenv("DISPATCHER_VIRTUAL_NODES", "128")
            ),
        )
