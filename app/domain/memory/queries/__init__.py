"""
HunterOS Engage — Memory Query & Retrieval Package
"""

from app.domain.memory.queries.bus import MemoryQueryBus
from app.domain.memory.queries.engines import (
    MemoryExportEngine,
    MemoryProjectionEngine,
    MemorySearchEngine,
    MemoryStatisticsEngine,
    ProjectionDefinition,
    ProjectionRegistry,
    QueryMetricsTracker,
    SearchCompiler,
)
from app.domain.memory.queries.facade import MemoryQueryFacade
from app.domain.memory.queries.filters import (
    FilterCompiler,
    FilterCondition,
    FilterGroup,
    FilterOperator,
)
from app.domain.memory.queries.handlers import (
    AbstractQueryHandler,
    BulkGetCustomerMemoryHandler,
    ExportPreviewHandler,
    GetCursorPaginatedMemoryHandler,
    GetCustomerMemoryHandler,
    GetProjectionHandler,
    GetStatisticsHandler,
    SearchCustomerMemoryHandler,
)
from app.domain.memory.queries.models import (
    BaseMemoryQuery,
    BulkGetCustomerMemoryQuery,
    CustomerMemoryDTO,
    ExecutiveViewDTO,
    ExportPreviewQuery,
    GetCursorPaginatedMemoryQuery,
    GetCustomerMemoryQuery,
    GetProjectionQuery,
    GetStatisticsQuery,
    LightweightViewDTO,
    MemoryExportColumn,
    MemoryExportDTO,
    MemoryStatisticsDTO,
    OperationalMetricsDTO,
    ProjectedMemoryDTO,
    SearchCustomerMemoryQuery,
    SummaryViewDTO,
)
from app.domain.memory.queries.pagination import (
    CursorCodec,
    CursorPaginatedResult,
    CursorPaginationParams,
    OffsetPaginatedResult,
    OffsetPaginationParams,
)
from app.domain.memory.queries.planner import (
    QueryExecutionPlan,
    QueryPlanner,
)
from app.domain.memory.queries.sorting import (
    SortCompiler,
    SortDirection,
    SortField,
)
from app.domain.memory.queries.specifications import (
    ActiveCustomersSpecification,
    AndSpecification,
    ArchivedCustomersSpecification,
    BudgetRangeSpecification,
    LifecycleSpecification,
    LocationSpecification,
    LockedCustomersSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
    TagSpecification,
    TrueSpecification,
    UpdatedRecentlySpecification,
    VersionSpecification,
    WorkspaceSpecification,
)

__all__ = [
    # Models & DTOs
    "BaseMemoryQuery",
    "GetCustomerMemoryQuery",
    "BulkGetCustomerMemoryQuery",
    "SearchCustomerMemoryQuery",
    "GetCursorPaginatedMemoryQuery",
    "GetProjectionQuery",
    "GetStatisticsQuery",
    "ExportPreviewQuery",
    "CustomerMemoryDTO",
    "ProjectedMemoryDTO",
    "SummaryViewDTO",
    "ExecutiveViewDTO",
    "LightweightViewDTO",
    "OperationalMetricsDTO",
    "MemoryStatisticsDTO",
    "MemoryExportColumn",
    "MemoryExportDTO",
    # Specifications
    "Specification",
    "AndSpecification",
    "OrSpecification",
    "NotSpecification",
    "ActiveCustomersSpecification",
    "ArchivedCustomersSpecification",
    "LockedCustomersSpecification",
    "WorkspaceSpecification",
    "LifecycleSpecification",
    "TagSpecification",
    "LocationSpecification",
    "BudgetRangeSpecification",
    "UpdatedRecentlySpecification",
    "VersionSpecification",
    "TrueSpecification",
    # Filtering & Sorting
    "FilterOperator",
    "FilterCondition",
    "FilterGroup",
    "FilterCompiler",
    "SortDirection",
    "SortField",
    "SortCompiler",
    # Pagination & Planning
    "OffsetPaginationParams",
    "OffsetPaginatedResult",
    "CursorPaginationParams",
    "CursorPaginatedResult",
    "CursorCodec",
    "QueryExecutionPlan",
    "QueryPlanner",
    # Engines
    "MemorySearchEngine",
    "SearchCompiler",
    "MemoryProjectionEngine",
    "ProjectionDefinition",
    "ProjectionRegistry",
    "MemoryStatisticsEngine",
    "QueryMetricsTracker",
    "MemoryExportEngine",
    # Handlers, Bus & Facade
    "AbstractQueryHandler",
    "GetCustomerMemoryHandler",
    "BulkGetCustomerMemoryHandler",
    "SearchCustomerMemoryHandler",
    "GetCursorPaginatedMemoryHandler",
    "GetProjectionHandler",
    "GetStatisticsHandler",
    "ExportPreviewHandler",
    "MemoryQueryBus",
    "MemoryQueryFacade",
]
