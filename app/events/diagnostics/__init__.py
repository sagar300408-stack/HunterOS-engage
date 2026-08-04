"""
HunterOS Engage — Runtime Diagnostics & Live Monitoring Platform
app/events/diagnostics/__init__.py
"""

from app.events.diagnostics.config import DiagnosticsConfig
from app.events.diagnostics.models import (
    BaseDiagnosticsReport,
    ConsumerDetail,
    ConsumerDiagnostics,
    DispatcherDetail,
    DispatcherDiagnostics,
    EarlyWarningIndicator,
    LiveInspectionQuery,
    LiveInspectionResult,
    LockDetail,
    LockDiagnostics,
    PartitionDetail,
    PartitionDiagnostics,
    QueueBreakdown,
    QueueDiagnostics,
    RuntimeHealthStatus,
    RuntimeHealthSummary,
    RuntimeSnapshot,
    SchedulerDetail,
    SchedulerDiagnostics,
    SubsystemHealthStatus,
    SubsystemType,
    WorkerDetail,
    WorkerDiagnostics,
)
from app.events.diagnostics.workers import (
    AbstractWorkerDiagnosticsCollector,
    DefaultWorkerDiagnosticsCollector,
)
from app.events.diagnostics.dispatchers import (
    AbstractDispatcherDiagnosticsCollector,
    DefaultDispatcherDiagnosticsCollector,
)
from app.events.diagnostics.queues import (
    AbstractQueueDiagnosticsCollector,
    DefaultQueueDiagnosticsCollector,
)
from app.events.diagnostics.partitions import (
    AbstractPartitionDiagnosticsCollector,
    DefaultPartitionDiagnosticsCollector,
)
from app.events.diagnostics.locks import (
    AbstractLockDiagnosticsCollector,
    DefaultLockDiagnosticsCollector,
)
from app.events.diagnostics.consumers import (
    AbstractConsumerDiagnosticsCollector,
    DefaultConsumerDiagnosticsCollector,
)
from app.events.diagnostics.scheduler import (
    AbstractSchedulerDiagnosticsCollector,
    DefaultSchedulerDiagnosticsCollector,
)
from app.events.diagnostics.health import (
    AbstractRuntimeHealthMonitor,
    DefaultRuntimeHealthMonitor,
)
from app.events.diagnostics.runtime import (
    AbstractRuntimeSnapshotGenerator,
    DefaultRuntimeSnapshotGenerator,
)
from app.events.diagnostics.inspection import (
    AbstractLiveInspectionService,
    DefaultLiveInspectionService,
)
from app.events.diagnostics.engine import (
    AbstractDiagnosticsEngine,
    DefaultDiagnosticsEngine,
)
from app.events.diagnostics.validator import DiagnosticsStartupValidator

# Global process-level singleton instance
diagnostics_engine = DefaultDiagnosticsEngine()

__all__ = [
    "DiagnosticsConfig",
    "BaseDiagnosticsReport",
    "SubsystemType",
    "RuntimeHealthStatus",
    "WorkerDetail",
    "WorkerDiagnostics",
    "DispatcherDetail",
    "DispatcherDiagnostics",
    "QueueBreakdown",
    "QueueDiagnostics",
    "PartitionDetail",
    "PartitionDiagnostics",
    "LockDetail",
    "LockDiagnostics",
    "ConsumerDetail",
    "ConsumerDiagnostics",
    "SchedulerDetail",
    "SchedulerDiagnostics",
    "EarlyWarningIndicator",
    "SubsystemHealthStatus",
    "RuntimeHealthSummary",
    "RuntimeSnapshot",
    "LiveInspectionQuery",
    "LiveInspectionResult",
    "AbstractWorkerDiagnosticsCollector",
    "DefaultWorkerDiagnosticsCollector",
    "AbstractDispatcherDiagnosticsCollector",
    "DefaultDispatcherDiagnosticsCollector",
    "AbstractQueueDiagnosticsCollector",
    "DefaultQueueDiagnosticsCollector",
    "AbstractPartitionDiagnosticsCollector",
    "DefaultPartitionDiagnosticsCollector",
    "AbstractLockDiagnosticsCollector",
    "DefaultLockDiagnosticsCollector",
    "AbstractConsumerDiagnosticsCollector",
    "DefaultConsumerDiagnosticsCollector",
    "AbstractSchedulerDiagnosticsCollector",
    "DefaultSchedulerDiagnosticsCollector",
    "AbstractRuntimeHealthMonitor",
    "DefaultRuntimeHealthMonitor",
    "AbstractRuntimeSnapshotGenerator",
    "DefaultRuntimeSnapshotGenerator",
    "AbstractLiveInspectionService",
    "DefaultLiveInspectionService",
    "AbstractDiagnosticsEngine",
    "DefaultDiagnosticsEngine",
    "DiagnosticsStartupValidator",
    "diagnostics_engine",
]
