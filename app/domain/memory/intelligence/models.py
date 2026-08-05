"""
HunterOS Engage — Memory Context & Intelligence Integration Models (Phase 2.1.5)

Defines domain models, enums, value objects, lineage tracking, completeness reporting,
and composed context representations for the Memory Context Integration Layer.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── Enums ─────────────────────────────────────────────────────────────────────

class ContextBlockType(str, enum.Enum):
    """Supported intelligence context building blocks."""
    MEMORY = "MEMORY"
    RELATIONSHIPS = "RELATIONSHIPS"
    TIMELINE = "TIMELINE"
    VERSIONS = "VERSIONS"
    STATISTICS = "STATISTICS"
    PROJECTIONS = "PROJECTIONS"
    AUDIT = "AUDIT"
    METADATA = "METADATA"
    CUSTOM = "CUSTOM"


class ContextCompletenessStatus(str, enum.Enum):
    """Diagnostic health and completeness status of a composed context."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INCOMPLETE = "INCOMPLETE"
    DEGRADED = "DEGRADED"


class ContextScope(str, enum.Enum):
    """Domain scope of the composed context."""
    CUSTOMER = "CUSTOMER"
    ORGANIZATION = "ORGANIZATION"
    OPPORTUNITY = "OPPORTUNITY"
    PROPERTY = "PROPERTY"
    EXECUTIVE = "EXECUTIVE"
    CUSTOM = "CUSTOM"


class ExportTargetFormat(str, enum.Enum):
    """Target output format for context serialization."""
    STANDARD_API = "STANDARD_API"
    EXECUTIVE = "EXECUTIVE"
    DASHBOARD = "DASHBOARD"
    STRUCTURED_CONTEXT = "STRUCTURED_CONTEXT"


# ── Value Objects & Lineage ───────────────────────────────────────────────────

@dataclass(frozen=True)
class ContextMetadata:
    """
    Metadata attached to every generated context for tracking and cache invalidation.
    """
    context_id: uuid.UUID
    context_version: int = 1
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"
    source_modules: List[str] = field(default_factory=lambda: ["memory_foundation", "knowledge_graph"])
    execution_time_ms: float = 0.0
    workspace_id: Optional[uuid.UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": str(self.context_id),
            "context_version": self.context_version,
            "generated_at": self.generated_at.isoformat(),
            "schema_version": self.schema_version,
            "source_modules": list(self.source_modules),
            "execution_time_ms": self.execution_time_ms,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
        }


@dataclass(frozen=True)
class ContextLineage:
    """
    Deterministic provenance tracking for every piece of composed context.
    Allows future AI, analytics, and audit systems to explain exact origin IDs.
    """
    source_memory_ids: List[str] = field(default_factory=list)
    source_relationship_ids: List[str] = field(default_factory=list)
    source_timeline_event_ids: List[str] = field(default_factory=list)
    projections_applied: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_modules: List[str] = field(default_factory=lambda: ["memory_foundation", "knowledge_graph", "timeline_audit"])
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_memory_ids": list(self.source_memory_ids),
            "source_relationship_ids": list(self.source_relationship_ids),
            "source_timeline_event_ids": list(self.source_timeline_event_ids),
            "projections_applied": list(self.projections_applied),
            "generated_at": self.generated_at.isoformat(),
            "source_modules": list(self.source_modules),
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ContextCompletenessReport:
    """
    Context completeness and diagnostic quality report.
    Never hallucinates or generates missing data.
    """
    score: float = 1.0
    status: ContextCompletenessStatus = ContextCompletenessStatus.COMPLETE
    total_blocks_requested: int = 0
    blocks_loaded: int = 0
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "status": self.status.value,
            "total_blocks_requested": self.total_blocks_requested,
            "blocks_loaded": self.blocks_loaded,
            "missing_fields": list(self.missing_fields),
            "warnings": list(self.warnings),
            "is_valid": self.is_valid,
        }


@dataclass
class ContextBlock:
    """
    A discrete composed block of information within a context.
    """
    block_type: ContextBlockType
    data: Dict[str, Any] = field(default_factory=dict)
    loaded: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_type": self.block_type.value,
            "data": self.data,
            "loaded": self.loaded,
            "error": self.error,
        }


# ── Composed Context ─────────────────────────────────────────────────────────

@dataclass
class ComposedContext:
    """
    Unified immutable aggregate container for composed context.
    Orchestrated by ContextComposer and produced by ContextPipeline.
    """
    scope: ContextScope
    entity_id: Optional[str]
    workspace_id: Optional[uuid.UUID]
    metadata: ContextMetadata
    lineage: ContextLineage
    completeness: ContextCompletenessReport
    blocks: Dict[ContextBlockType, ContextBlock] = field(default_factory=dict)

    def get_block(self, block_type: ContextBlockType) -> Optional[ContextBlock]:
        return self.blocks.get(block_type)

    def get_block_data(self, block_type: ContextBlockType) -> Dict[str, Any]:
        block = self.blocks.get(block_type)
        return block.data if block and block.loaded else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope.value,
            "entity_id": self.entity_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "metadata": self.metadata.to_dict(),
            "lineage": self.lineage.to_dict(),
            "completeness": self.completeness.to_dict(),
            "blocks": {k.value: v.to_dict() for k, v in self.blocks.items()},
        }
